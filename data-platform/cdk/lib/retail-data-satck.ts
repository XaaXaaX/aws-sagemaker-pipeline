import { ArnFormat, RemovalPolicy, Stack } from 'aws-cdk-lib';
import { Bucket, BucketEncryption } from 'aws-cdk-lib/aws-s3';

import { Construct } from 'constructs';
import { EnforcedStack, EnforcedStackProps } from '@helpers';
import { BucketDeployment, Source } from 'aws-cdk-lib/aws-s3-deployment';
import { AccountPrincipal, PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { StringParameter } from 'aws-cdk-lib/aws-ssm';
import { DataConfig } from '../config';
import { Key } from 'aws-cdk-lib/aws-kms';

export interface RetailDataStackProps extends EnforcedStackProps {
  orga: DataConfig['orga'];
}
export class RetailDataStack extends EnforcedStack {

  constructor(scope: Construct, id: string, props: RetailDataStackProps) {
    super(scope, id, props);

    const { orga } = props;

    const orgAccountIds = orga.accounts.map((account) => {
      const accountParameterArn = Stack.of(this).formatArn({
        service: 'ssm', 
        region: this.REGION,
        account: orga.orgaAccountId,
        resource: 'parameter', 
        resourceName: `${this.ENV}/infra-shared/${account.accountName}/account/id`,
        arnFormat: ArnFormat.SLASH_RESOURCE_NAME,
      })
      return StringParameter.fromStringParameterArn(this, `${account.accountName}SharedParam`, accountParameterArn).stringValue;
    });

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

    const dataSourceBucket = new Bucket(this, 'DataSourceBucket', {
      bucketName: `${this.CONTEXT}-source-bucket-${this.REGION}-${this.ACCOUNT_ID}`,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      encryption: BucketEncryption.KMS,
      encryptionKey,
      enforceSSL: true,
    });

    const deployment = new BucketDeployment(this, 'DataSourceBucketDeployment', {
      destinationBucket: dataSourceBucket,
      sources: [ Source.asset('./data-platform/data') ],
    });

    encryptionKey.grantEncryptDecrypt(deployment.handlerRole);

    dataSourceBucket.addToResourcePolicy(new PolicyStatement({
      actions: [ 's3:Get*', 's3:List*' ],
      resources: [ 
        dataSourceBucket.bucketArn,
        dataSourceBucket.arnForObjects('*'),
      ],
      principals: orgAccountIds.map((id) => new AccountPrincipal(id)),
      conditions: {
        ArnLike: {
          'aws:PrincipalArn': orgAccountIds.map((account) => {
            return `arn:aws:iam::${account}:role/*`  
          })
        },
      }
    }))
  }
}
