/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Server as HttpServer } from "http";
import compression from "compression";
import cors from "cors";
import type { Express, Request, Response, Router } from "express";
import express from "express";
import helmet from "helmet";
// plane imports
import { registerController } from "@plane/decorators";
import { logger, loggerMiddleware } from "@plane/logger";
// controllers
import { CONTROLLERS } from "@/controllers";
// env
import { env } from "@/env";

export class Server {
  private app: Express;
  private router: Router;
  private httpServer: HttpServer | undefined;

  constructor() {
    this.app = express();
    this.setupMiddleware();
    this.router = express.Router();
    this.app.set("port", env.PORT || 3000);
    this.app.use(env.LIVE_BASE_PATH, this.router);
  }

  public async initialize(): Promise<void> {
    try {
      this.setupRoutes();
      this.setupNotFoundHandler();
    } catch (error) {
      logger.error("SERVER: Failed to initialize live server dependencies:", error);
      throw error;
    }
  }

  private setupMiddleware() {
    // Security middleware
    this.app.use(helmet());
    // Middleware for response compression
    this.app.use(compression({ level: env.COMPRESSION_LEVEL, threshold: env.COMPRESSION_THRESHOLD }));
    // Logging middleware
    this.app.use(loggerMiddleware);
    // Body parsing middleware
    this.app.use(express.json());
    this.app.use(express.urlencoded({ extended: true }));
    // cors middleware
    this.setupCors();
  }

  private setupCors() {
    const allowedOrigins = env.CORS_ALLOWED_ORIGINS.split(",").map((s) => s.trim());
    this.app.use(
      cors({
        origin: allowedOrigins.length > 0 ? allowedOrigins : false,
        credentials: true,
        methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allowedHeaders: ["Content-Type", "Authorization", "x-api-key"],
      })
    );
  }

  private setupNotFoundHandler() {
    this.app.use((_req: Request, res: Response) => {
      res.status(404).json({
        message: "Not Found",
      });
    });
  }

  private setupRoutes() {
    CONTROLLERS.forEach((controller) => registerController(this.router, controller, []));
  }

  public listen() {
    this.httpServer = this.app
      .listen(this.app.get("port"), () => {
        logger.info(`SERVER: Express server has started at port ${this.app.get("port")}`);
      })
      .on("error", (err) => {
        logger.error("SERVER: Failed to start server:", err);
        throw err;
      });
  }

  public async destroy() {
    if (this.httpServer) {
      await new Promise<void>((resolve, reject) => {
        this.httpServer!.close((err) => {
          if (err) {
            reject(err);
          } else {
            logger.info("SERVER: Express server closed gracefully.");
            resolve();
          }
        });
      });
    }
  }
}
