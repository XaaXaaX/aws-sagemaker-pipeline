import { Config, EnvVariable } from "@type";

const getFinalConfig = <T extends Config>(config: Partial<Config>, defaultConfig: T): T => {
  return {
    ...defaultConfig,
    contextVariables: {
      ...defaultConfig.contextVariables,
      ...config.contextVariables,
    },
    ...config
  } as T
}


export const getConfig = <T extends Config>(stage: EnvVariable, defaultConfig: T): T => {
  switch (stage) {
    case 'test':
      return getFinalConfig({ contextVariables: { ...defaultConfig.contextVariables, stage: 'test', usage: 'PRODUCTION' } }, defaultConfig );
    case 'prod':
      return getFinalConfig({ contextVariables: { ...defaultConfig.contextVariables, stage: 'prod', usage: 'PRODUCTION' } }, defaultConfig );
    case 'dev':
      return getFinalConfig({ contextVariables: { ...defaultConfig.contextVariables, stage: 'dev', usage: 'DEVELOPMENT' } }, defaultConfig );
    case 'sandbox':
      return getFinalConfig({ contextVariables: { ...defaultConfig.contextVariables, stage: 'sandbox', usage: 'POC' } }, defaultConfig );
    default:
      return getFinalConfig({}, defaultConfig);
  }
};