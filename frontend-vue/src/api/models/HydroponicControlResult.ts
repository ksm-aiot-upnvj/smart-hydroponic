/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type HydroponicControlResult = {
  pump_status?: boolean;
  light_status?: boolean;
  automation_status?: boolean;
  command_id: string;
  confirmed?: boolean;
  delivery_status?: "confirmed" | "dispatched" | "unavailable" | "failed";
};
