#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { RetailDataStack } from '../lib/retail-data-satck';
import { getEnv } from '@helpers';
import { getConfig } from '../config';

const app = new cdk.App();
const environment = getEnv(app);
const { contextVariables, orga } = getConfig(environment);
new RetailDataStack(app, `${contextVariables.context}-${RetailDataStack.name}-${contextVariables.stage}`, {
  contextVariables,
  orga,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  }
});
