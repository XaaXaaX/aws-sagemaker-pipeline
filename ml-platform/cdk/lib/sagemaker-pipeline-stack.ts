import { ArnFormat, RemovalPolicy, Stack } from 'aws-cdk-lib';
import { Repository } from 'aws-cdk-lib/aws-ecr';

import { Effect, ManagedPolicy, PolicyDocument, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Bucket, ObjectOwnership } from 'aws-cdk-lib/aws-s3';
import { CfnPipeline } from 'aws-cdk-lib/aws-sagemaker';

import { Construct } from 'constructs';
import { EnforcedStack, EnforcedStackProps } from '../core/helpers';
import { AppConfig } from '../configs';
import { StringParameter } from 'aws-cdk-lib/aws-ssm';
import { Key } from 'aws-cdk-lib/aws-kms';

export interface SagemakerPipelineStackProps extends EnforcedStackProps {
  orga: AppConfig['orga']
}
export class SagemakerPipelineStack extends EnforcedStack {

  constructor(scope: Construct, id: string, props: SagemakerPipelineStackProps) {
    super(scope, id, props);

    const { orga } = props;
    
    const dataAccountParameterArn = Stack.of(this).formatArn({
      service: 'ssm', 
      region: this.REGION,
      account: orga.orgaAccountId,
      resource: 'parameter', 
      resourceName: `${this.ENV}/infra-shared/data_platform_b/account/id`,
      arnFormat: ArnFormat.SLASH_RESOURCE_NAME,
    });
    const dataplatformAccount = StringParameter.fromStringParameterArn(this, `DataAccountSharedParam`, dataAccountParameterArn).stringValue;

    const encryptionParameterArn = Stack.of(this).formatArn({
      service: 'ssm', 
      region: this.REGION,
      account: orga.orgaAccountId,
      resource: 'parameter', 
      resourceName: `${this.ENV}/infra-shared/shared/encryption/key/arn`,
      arnFormat: ArnFormat.SLASH_RESOURCE_NAME,
    })
    const encryptionKeyArnParam = StringParameter.fromStringParameterArn(this, 'EncryptionKeyArnParam', encryptionParameterArn ).stringValue;
    const encryptionKey = Key.fromKeyArn(this, 'EncryptionKey', encryptionKeyArnParam);

    const repository = new Repository(this, 'EcrRepository', {
      repositoryName: `${this.CONTEXT}-processing-model-${this.ENV}`,
      removalPolicy: RemovalPolicy.DESTROY,
      emptyOnDelete: true,
      imageScanOnPush: true, 
    });

    // aws ecr get-login-password --region eu-west-1 --profile admin@ml | docker login --username AWS --password-stdin 147997120184.dkr.ecr.eu-west-1.amazonaws.com
    // ECR_REPOSITORY="147997120184.dkr.ecr.eu-west-1.amazonaws.com/mlops-sagemaker-processing-model-dev"
    // docker buildx build --platform linux/amd64 --no-cache -t ${ECR_REPOSITORY}:1234566 .
    // docker tag ${ECR_REPOSITORY}:1234566 ${ECR_REPOSITORY}:latest
    // docker push ${ECR_REPOSITORY}:1234566
    // docker push ${ECR_REPOSITORY}:latest
    // aws sagemaker start-pipeline-execution --pipeline-name pipeline-attractivity-score-training-${ENV}
    // new DockerImageAsset(this, 'DockerImageAsset', {
    //   directory: join(process.cwd(), './src/processing'),
    // });

    const featurebucket = new Bucket(this, 'FeatureBucket', {
      bucketName: `${this.CONTEXT}-feature-bucket-${this.REGION}-${this.ACCOUNT_ID}`,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_PREFERRED,
      enforceSSL: true,
    });

    const dataSourceBucket = Bucket.fromBucketName(this, 'DataSourceBucket', `data-platform-source-bucket-${this.REGION}-${dataplatformAccount}`);

    const sagemakerRole = new Role(this, 'SageMakerRole', {
      assumedBy: new ServicePrincipal('sagemaker.amazonaws.com'),

      managedPolicies: [
        ManagedPolicy.fromAwsManagedPolicyName('AmazonS3FullAccess'),
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerFullAccess'),
      ],
      inlinePolicies: {
        SageMakerPolicy: new PolicyDocument({
          // PassRole
          statements: [
            new PolicyStatement({
              effect: Effect.ALLOW,
              actions: ['iam:PassRole'],
              resources: ['*'],
              conditions: {
                StringEquals: { "iam:PassedToService": [ "sagemaker.amazonaws.com" ] }
              }
            }),
          ],
        }),
      }
    });


    // Define the SageMaker Pipeline
    const pipelineDefinition = JSON.stringify({
      Version: '2020-12-01',
      Steps: [
        {
          Name: 'DataProcessing',
          Type: 'Processing',
          Arguments: {
            ProcessingJobName: 'DataProcessing',
            RoleArn: sagemakerRole.roleArn,
            AppSpecification: {
              ImageUri: `${this.ACCOUNT_ID}.dkr.ecr.${this.REGION}.amazonaws.com/${this.CONTEXT}-processing-model-${this.ENV}:latest`
            },
            ProcessingInputs: [
              {
                InputName: 'processing-input',
                S3Input: {
                  S3Uri: `s3://${dataSourceBucket.bucketName}/${this.CONTEXT}/input/`,
                  LocalPath: '/opt/ml/processing/input',
                  S3DataType: 'S3Prefix',
                },
              },
            ],
            ProcessingOutputConfig: {
              Outputs: [
                {
                  OutputName: 'processing-output',
                  S3Output: {
                    S3Uri: `s3://${featurebucket.bucketName}/${this.CONTEXT}/output/`,
                    LocalPath: '/opt/ml/processing/output',
                    S3UploadMode: 'EndOfJob',
                  },
                },
              ],
            },
            ProcessingResources: {
              ClusterConfig: {
                InstanceType: 'ml.t3.medium',
                InstanceCount: 1,
                VolumeSizeInGB: 1,
              },
            },
          },
        },
        {
          Name: 'TrainingStep',
          Type: 'Training',
          DependsOn: ['DataProcessingTraining'],
          Arguments: {
            TrainingJobName: 'TrainingStep',
            AlgorithmSpecification: {
              TrainingImage: `${this.ACCOUNT_ID}.dkr.ecr.${this.REGION}.amazonaws.com/${this.CONTEXT}-training-model-${this.ENV}:latest`,
              TrainingInputMode: 'File',
            },
            HyperParameters: {
              early_stopping_rounds: ['3000'],
              loss_function: ['YetiRank'],
              iterations: ['10000'],
              learning_rate: ['0.15'],
              l2_leaf_reg: ['8'],
              depth: ['6'],
            },
            RoleArn: sagemakerRole.roleArn,
            StoppingCondition: {
              MaxRuntimeInSeconds: 300,
            },
            OutputDataConfig: {
              S3OutputPath: `s3://${featurebucket.bucketName}/inference.csv`,
            },
            InputDataConfig: [
              {
                ChannelName: 'training-input',
                DataSource: {
                  S3DataSource: {
                    S3Uri: `s3://${featurebucket.bucketName}/${this.CONTEXT}/output/`,
                    LocalPath: '/opt/ml/processing/input/',
                    S3DataType: 'S3Prefix',
                  },
                },
              },
            ],
            ResourceConfig: {
              InstanceType: 'ml.t3.medium',
              InstanceCount: 1,
              VolumeSizeInGB: 1,
            },
          },
        },
        {
          Name: 'RegisterModelStep',
          Type: 'RegisterModel',
          DependsOn: ['TrainingStep'],
          Arguments: {
            ModelPackageGroupName: `sagemaker-package_group`,
            ModelApprovalStatus: 'PendingManualApproval',
            InferenceSpecification: {
              Containers: [
                {
                  Image: `${this.ACCOUNT_ID}.dkr.ecr.${this.REGION}.amazonaws.com/${this.CONTEXT}-inference-${this.ENV}:latest`,
                  ModelDataUrl: {
                    Get: 'Steps.TrainingStep.ModelArtifacts.S3ModelArtifacts',
                  },
                },
              ],
              SupportedContentTypes: ['application/json'],
              SupportedResponseMIMETypes: ['application/json'],
            },
          },
        },
      ],
    });

    const pipelineTraining = new CfnPipeline(this, 'SageMakerPipelineTraining', {
      pipelineName: `sagemaker-retail-stock-training-pipeline`,
      pipelineDefinition: {
        PipelineDefinitionBody: pipelineDefinition,
      },
      roleArn: sagemakerRole.roleArn,
    });

    // Define the EventBridge rule directly in CloudFormation using a Custom Resource
    // new CfnResource(this, 'EventRuleTraining', {
    //   type: 'AWS::Events::Rule',
    //   properties: {
    //     Name: `sagemaker-rule-training`,
    //     ScheduleExpression: 'cron(0 8 1 1,4,7,10 ? *)',
    //     State: 'DISABLED',
    //     Targets: [
    //       {
    //         Arn: `arn:aws:sagemaker:${this.REGION}:${this.ACCOUNT_ID}:pipeline/${PipelineTraining.pipelineName}`,
    //         Id: 'Target0',
    //         RoleArn: sagemakerRole.roleArn,
    //       },
    //     ],
    //   },
    // });

    
    featurebucket.grantReadWrite(sagemakerRole);
    dataSourceBucket.grantRead(sagemakerRole);
    repository.grantPull(sagemakerRole);
    encryptionKey.grantEncryptDecrypt(sagemakerRole);
  }

}
