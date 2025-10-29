import { EnvVariable, Config } from "@type";
import { getConfig as SharedGetConfig } from "@config";

const defaultConfig: Config = {
  contextVariables: {
    context: `mlops-sagemaker`,
    stage: 'unknown' as EnvVariable, 
    owner: 'operations',
    usage: 'EPHEMERAL',
  },
}

export const getConfig = (stage: EnvVariable): Config => {
  return SharedGetConfig(stage, defaultConfig);
};