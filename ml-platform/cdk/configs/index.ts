import { EnvVariable, Config } from "@type";
import { getConfig as SharedGetConfig } from "@config";

export type OrgConfig = {
  orgaAccountId: string,
  accounts: { accountName: string }[]
}

export type AppConfig = Config & {
  orga: OrgConfig
};

const defaultConfig: AppConfig = {
  contextVariables: {
    context: `mlops-sagemaker`,
    stage: 'unknown' as EnvVariable, 
    owner: 'operations',
    usage: 'EPHEMERAL',
  },
  orga: {
    orgaAccountId: '607050363559',
    accounts: [
      { accountName: 'data_platform_b' }
    ]
  }
}

export const getConfig = (stage: EnvVariable): AppConfig => {
  return SharedGetConfig(stage, defaultConfig);
};