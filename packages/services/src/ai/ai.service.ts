/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane web constants
import type { AI_EDITOR_TASKS } from "@plane/constants";
import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "../api.service";

/**
 * Payload type for AI editor tasks
 * @typedef {Object} TTaskPayload
 * @property {number} [casual_score] - Optional score for casual tone analysis
 * @property {number} [formal_score] - Optional score for formal tone analysis
 * @property {AI_EDITOR_TASKS} task - Type of AI editor task to perform
 * @property {string} text_input - The input text to be processed
 */
export type TTaskPayload = {
  casual_score?: number;
  formal_score?: number;
  task: AI_EDITOR_TASKS;
  text_input: string;
};

/**
 * Service class for handling AI-related API operations
 * Extends the base APIService class to interact with AI endpoints
 * @extends {APIService}
 */
export class AIService extends APIService {
  constructor(BASE_URL?: string) {
    super(BASE_URL || API_BASE_URL);
  }

  /**
   * Creates a GPT-based task for a specific workspace
   * @param {Object} data - The data payload for the GPT task
   * @param {string} data.prompt - The prompt text for the GPT model
   * @param {string} data.task - The type of task to be performed
   * @returns {Promise<any>} The response data from the GPT task
   * @throws {Error} Throws the response error if the request fails
   */
  async prompt(data: { prompt: string; task: string }): Promise<any> {
    return this.post(`/api/workspace/ai-assistant/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  /**
   * Performs an editor-specific AI task for text processing
   * @param {TTaskPayload} data - The task payload containing text and processing parameters
   * @returns {Promise<{response: string}>} The processed text response
   * @throws {Error} Throws the response data if the request fails
   */
  async rephraseGrammar(data: TTaskPayload): Promise<{
    response: string;
  }> {
    return this.post(`/api/workspace/rephrase-grammar/`, data)
      .then((res) => res?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
