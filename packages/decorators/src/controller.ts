/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { RequestHandler, Router } from "express";

import "reflect-metadata";

export type HttpMethod = "get" | "post" | "put" | "delete" | "patch" | "options" | "head";

type ControllerInstance = {
  [key: string]: any;
};

export type ControllerConstructor = {
  new (...args: any[]): ControllerInstance;
  prototype: ControllerInstance;
};

export function registerController(
  router: Router,
  Controller: ControllerConstructor,
  dependencies: unknown[] = []
): void {
  // Create the controller instance with dependencies
  const instance = new Controller(...dependencies);
  registerRestController(router, Controller, instance);
}

function registerRestController(
  router: Router,
  Controller: ControllerConstructor,
  existingInstance?: ControllerInstance
): void {
  const instance = existingInstance || new Controller();
  const baseRoute = Reflect.getMetadata("baseRoute", Controller) as string;

  Object.getOwnPropertyNames(Controller.prototype).forEach((methodName) => {
    if (methodName === "constructor") return; // Skip the constructor

    const method = Reflect.getMetadata("method", instance, methodName) as HttpMethod;
    const route = Reflect.getMetadata("route", instance, methodName) as string;
    const middlewares = (Reflect.getMetadata("middlewares", instance, methodName) as RequestHandler[]) || [];

    if (method && route) {
      const handler = instance[methodName] as unknown;

      if (typeof handler === "function") {
        (router[method] as (path: string, ...handlers: RequestHandler[]) => void)(
          `${baseRoute}${route}`,
          ...middlewares,
          handler.bind(instance)
        );
      }
    }
  });
}
