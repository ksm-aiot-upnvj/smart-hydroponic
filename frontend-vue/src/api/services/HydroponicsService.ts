/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HydroponicControlResult } from "../models/HydroponicControlResult";
import type { HydroponicDashboardOut } from "../models/HydroponicDashboardOut";
import type { HydroponicDataActuator } from "../models/HydroponicDataActuator";
import type { ResponseList_HydroponicOut_ } from "../models/ResponseList_HydroponicOut_";
import type { CancelablePromise } from "../core/CancelablePromise";
import { OpenAPI } from "../core/OpenAPI";
import { request as __request } from "../core/request";
export class HydroponicsService {
  /**
   * Get Latest Hydroponic Data
   * @returns any Successful Response
   * @throws ApiError
   */
  public static getLatestHydroponicData(): CancelablePromise<HydroponicDashboardOut | null> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/hydroponics/data/latest",
    });
  }
  /**
   * Get Specific Hydroponic Data
   * @param parameter
   * @param page
   * @param limit
   * @param startDate
   * @param endDate
   * @returns ResponseList_HydroponicOut_ Successful Response
   * @throws ApiError
   */
  public static getSpecificHydroponicData(
    parameter: string,
    page: number = 1,
    limit: number = 25,
    startDate?: string | null,
    endDate?: string | null,
  ): CancelablePromise<ResponseList_HydroponicOut_> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/hydroponics/data/{parameter}",
      path: {
        parameter: parameter,
      },
      query: {
        page: page,
        limit: limit,
        start_date: startDate,
        end_date: endDate,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get Hydroponic Data
   * @param page
   * @param limit
   * @param startDate
   * @param endDate
   * @returns ResponseList_HydroponicOut_ Successful Response
   * @throws ApiError
   */
  public static getHydroponicData(
    page: number = 1,
    limit: number = 25,
    startDate?: string | null,
    endDate?: string | null,
  ): CancelablePromise<ResponseList_HydroponicOut_> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/hydroponics/data",
      query: {
        page: page,
        limit: limit,
        start_date: startDate,
        end_date: endDate,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get Public Hydroponic Data
   * Endpoint publik untuk mendapatkan data hidroponik terbaru tanpa autentikasi.
   * @param page
   * @param limit
   * @param startDate
   * @param endDate
   * @returns ResponseList_HydroponicOut_ Successful Response
   * @throws ApiError
   */
  public static getPublicHydroponicData(
    page: number = 1,
    limit: number = 25,
    startDate?: string | null,
    endDate?: string | null,
  ): CancelablePromise<ResponseList_HydroponicOut_> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/hydroponics/public",
      query: {
        page: page,
        limit: limit,
        start_date: startDate,
        end_date: endDate,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Control Hydroponic Actuators
   * Forward dashboard commands to the actuator and wait for device ACK.
   *
   * This supports Scenario 3 evaluation. The command is tagged with a
   * command_id, then sent to the actuator using WebSocket or CoAP. CoAP mode is
   * selected with `?transport=coap`.
   * @param requestBody
   * @param transport
   * @returns HydroponicControlResult Successful Response
   * @throws ApiError
   */
  public static controlHydroponicActuators(
    requestBody: HydroponicDataActuator,
    transport: string = "websocket",
  ): CancelablePromise<HydroponicControlResult> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/hydroponics/control",
      query: {
        transport: transport,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Test Sensor Data
   * Endpoint untuk menguji WebSocket sensor data hidroponik.
   * @returns string Successful Response
   * @throws ApiError
   */
  public static testSensorDataHydroponicsTestSensorDataGet(): CancelablePromise<string> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/hydroponics/test-sensor-data",
    });
  }
}
