import type { Settings } from "./Utils";

type CurrentSingleCoCoSettingsResponse = {
  supported: boolean;
  settings: Settings;
};

type LegacySingleCoCoSettingsResponse = Settings & {
  supported: boolean;
};

export type SingleCoCoSettingsResponse = CurrentSingleCoCoSettingsResponse | LegacySingleCoCoSettingsResponse;

export function normalizeSingleCoCoSettingsResponse(
  response: SingleCoCoSettingsResponse
): CurrentSingleCoCoSettingsResponse {
  if ("settings" in response) {
    return response;
  }

  const { supported, ...settings } = response;
  return { supported, settings };
}
