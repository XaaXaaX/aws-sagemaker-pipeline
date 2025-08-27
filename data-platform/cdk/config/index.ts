import { getConfig as SharedGetConfig } from "@config";
import { Config, EnvVariable } from "@type";

export type OrgConfig = {
  orgaAccountId: string,
  accounts: {
    accountName: string
  }[]
}

export type DataConfig = Config & {
  orga: OrgConfig
};

const defaultConfig: DataConfig = {
  contextVariables: {
    context: `data-platform`,
    stage: 'unknown' as EnvVariable, 
    owner: 'operations',
    usage: 'EPHEMERAL',
  },
  orga: {
    orgaAccountId: '607050363559',
    accounts: [
      { accountName: 'ml_platform_b' }
    ]
  }
}

export const getConfig = (stage: EnvVariable): DataConfig => {
  return SharedGetConfig(stage, defaultConfig);
};