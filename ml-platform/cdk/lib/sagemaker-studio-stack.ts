import { SubnetType, Vpc } from 'aws-cdk-lib/aws-ec2';

import {  Effect, ManagedPolicy, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { CfnDomain, CfnUserProfile } from 'aws-cdk-lib/aws-sagemaker';

import { Construct } from 'constructs';
import { EnforcedStack, EnforcedStackProps } from '../core/helpers';

export interface SagemakerStudioStackProps extends EnforcedStackProps { }
export class SagemakerStudioStack extends EnforcedStack {

  constructor(scope: Construct, id: string, props: SagemakerStudioStackProps) {
    super(scope, id, props);


    const vpc = Vpc.fromLookup(this, 'VPC', { isDefault: true });
    const vpcPublicSubnets = vpc.selectSubnets({ subnetType: SubnetType.PUBLIC });
    const sagemakerDefaultExecutionRole = new Role(this, 'SageMakerExecutionRole', {
      assumedBy: new ServicePrincipal('sagemaker.amazonaws.com'),
      description: 'SageMaker execution role',
      managedPolicies: [
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerModelGovernanceUseAccess'),
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerPipelinesIntegrations'),
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerModelRegistryFullAccess'),
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerFeatureStoreAccess'),
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerGroundTruthExecution'),  
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerPipelinesIntegrations'),
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerReadOnly')
      ],
    });  

    sagemakerDefaultExecutionRole.addToPolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sagemaker:CreatePipeline',
        'sagemaker:StartPipelineExecution',
        'sagemaker:StopPipelineExecution',
        'sagemaker:RetryPipelineExecution',
        'sagemaker:ListPipelineExecutionSteps',
      ],
      resources: ['*'],
    }));  

    const defaultUserSettings = { executionRole: sagemakerDefaultExecutionRole.roleArn };

    const domain = new CfnDomain(this, 'SageMakerDomain', {
      authMode: 'IAM', // you can set it to 'IAM' or 'SSO'
      domainName: `${this.CONTEXT}-full-machine-learning-${this.ENV}`,
      defaultUserSettings,
      subnetIds: vpcPublicSubnets.subnetIds,
      vpcId: vpc.vpcId,
      tagPropagation: 'ENABLED'
    });

    new CfnUserProfile(this, `SageMakerUserProfile`, {
      domainId: domain.ref,
      // singleSignOnUserIdentifier: 'UserName', // Just for SSO
      // singleSignOnUserValue: 'My_User', // Just for SSO
      userSettings: {
        executionRole: sagemakerDefaultExecutionRole.roleArn
      },
      userProfileName: `${this.CONTEXT}-powered-user-profile-${this.ENV}`,
    });
  };
}
