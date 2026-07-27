import type { Settings } from "./Utils";

type CurrentSingleCoCoSettingsResponse = {
  supported: boolean;
  settings: Settings;
};

type LegacySingleCoCoSettingsResponse = Omit<Settings, "attestOnSchedule"> & {
  supported: boolean;
  attestOnSchedule?: Settings["attestOnSchedule"];
};

export type SingleCoCoSettingsResponse = CurrentSingleCoCoSettingsResponse | LegacySingleCoCoSettingsResponse;

export function normalizeSingleCoCoSettingsResponse(
  response: SingleCoCoSettingsResponse
): CurrentSingleCoCoSettingsResponse {
  if ("settings" in response) {
    return response;
  }

  const { supported, attestOnSchedule = false, ...settings } = response;
  return { supported, settings: { ...settings, attestOnSchedule } };
}
