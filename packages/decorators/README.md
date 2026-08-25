# @plane/decorators

A lightweight TypeScript decorator library for building Express.js controllers with a clean, declarative syntax.

## Features

- TypeScript-first design
- Decorators for HTTP methods (GET, POST, PUT, PATCH, DELETE)
- Middleware support
- No build step required - works directly with TypeScript files

## Installation

This package is part of the Plane workspace and can be used by adding it to your project's dependencies:

```json
{
  "dependencies": {
    "@plane/decorators": "workspace:*"
  }
}
```

## Usage

### Basic REST Controller

```typescript
import { Controller, Get, Post, BaseController } from "@plane/decorators";
import { Router, Request, Response } from "express";

@Controller("/api/users")
class UserController extends BaseController {
  @Get("/")
  async getUsers(req: Request, res: Response) {
    return res.json({ users: [] });
  }

  @Post("/")
  async createUser(req: Request, res: Response) {
    return res.json({ success: true });
  }
}

// Register routes
const router = Router();
const userController = new UserController();
userController.registerRoutes(router);
```

## API Reference

### Decorators

- `@Controller(baseRoute: string)` - Class decorator for defining a base route
- `@Get(route: string)` - Method decorator for HTTP GET endpoints
- `@Post(route: string)` - Method decorator for HTTP POST endpoints
- `@Put(route: string)` - Method decorator for HTTP PUT endpoints
- `@Patch(route: string)` - Method decorator for HTTP PATCH endpoints
- `@Delete(route: string)` - Method decorator for HTTP DELETE endpoints
- `@Middleware(middleware: RequestHandler)` - Method decorator for applying middleware

### Classes

- `BaseController` - Base class for REST controllers

## License

This project is licensed under the [GNU Affero General Public License v3.0](https://github.com/makeplane/plane/blob/master/LICENSE.txt).
