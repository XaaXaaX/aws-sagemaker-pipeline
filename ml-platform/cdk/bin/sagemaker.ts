#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SagemakerPipelineStack } from '../lib/sagemaker-pipeline-stack';
import { SagemakerStudioStack } from '../lib/sagemaker-studio-stack';
import { getConfig } from '../configs';
import { getEnv } from '../core/helpers';

const app = new cdk.App();
const environment = getEnv(app);
const { contextVariables, orga } = getConfig(environment);
const currentEnv = { region: process.env.CDK_DEFAULT_REGION, account: process.env.CDK_DEFAULT_ACCOUNT };

new SagemakerStudioStack(app, SagemakerStudioStack.name, {
  contextVariables,
  env: currentEnv,
});
new SagemakerPipelineStack(app, SagemakerPipelineStack.name, {
  contextVariables,
  orga,
  env: currentEnv,
});
