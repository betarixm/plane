/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { AxiosRequestConfig } from "axios";
// plane types
import { API_BASE_URL } from "@plane/constants";
import { getFileMetaDataForUpload, generateFileUploadPayload } from "@plane/services";
import type { EFileAssetType, TFileEntityInfo, TFileSignedURLResponse } from "@plane/types";
import { getAssetIdFromUrl } from "@plane/utils";
// helpers
// services
import { APIService } from "@/services/api.service";
import { FileUploadService } from "@/services/file-upload.service";

export interface UnSplashImage {
  id: string;
  created_at: Date;
  updated_at: Date;
  promoted_at: Date;
  width: number;
  height: number;
  color: string;
  blur_hash: string;
  description: null;
  alt_description: string;
  urls: UnSplashImageUrls;
  [key: string]: any;
}

export interface UnSplashImageUrls {
  raw: string;
  full: string;
  regular: string;
  small: string;
  thumb: string;
  small_s3: string;
}

export class FileService extends APIService {
  private cancelSource: any;
  private fileUploadService: FileUploadService;

  constructor() {
    super(API_BASE_URL);
    this.cancelUpload = this.cancelUpload.bind(this);
    // upload service
    this.fileUploadService = new FileUploadService();
  }

  private async updateWorkspaceAssetUploadStatus(assetId: string): Promise<void> {
    return this.patch(`/api/assets/v2/workspace/${assetId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async uploadWorkspaceAsset(
    data: TFileEntityInfo,
    file: File,
    uploadProgressHandler?: AxiosRequestConfig["onUploadProgress"]
  ): Promise<TFileSignedURLResponse> {
    const fileMetaData = await getFileMetaDataForUpload(file);
    return this.post(`/api/assets/v2/workspace/`, {
      ...data,
      ...fileMetaData,
    })
      .then(async (response) => {
        const signedURLResponse: TFileSignedURLResponse = response?.data;
        const fileUploadPayload = generateFileUploadPayload(signedURLResponse, file);
        await this.fileUploadService.uploadFile(
          signedURLResponse.upload_data.url,
          fileUploadPayload,
          uploadProgressHandler
        );
        await this.updateWorkspaceAssetUploadStatus(signedURLResponse.asset_id);
        return signedURLResponse;
      })
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  private async updateProjectAssetUploadStatus(projectId: string, assetId: string): Promise<void> {
    return this.patch(`/api/assets/v2/workspace/projects/${projectId}/${assetId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateBulkWorkspaceAssetsUploadStatus(
    entityId: string,
    data: {
      asset_ids: string[];
    }
  ): Promise<void> {
    return this.post(`/api/assets/v2/workspace/${entityId}/bulk/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateBulkProjectAssetsUploadStatus(
    projectId: string,
    entityId: string,
    data: {
      asset_ids: string[];
    }
  ): Promise<void> {
    return this.post(`/api/assets/v2/workspace/projects/${projectId}/${entityId}/bulk/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async uploadProjectAsset(
    projectId: string,
    data: TFileEntityInfo,
    file: File,
    uploadProgressHandler?: AxiosRequestConfig["onUploadProgress"]
  ): Promise<TFileSignedURLResponse> {
    const fileMetaData = await getFileMetaDataForUpload(file);
    return this.post(`/api/assets/v2/workspace/projects/${projectId}/`, {
      ...data,
      ...fileMetaData,
    })
      .then(async (response) => {
        const signedURLResponse: TFileSignedURLResponse = response?.data;
        const fileUploadPayload = generateFileUploadPayload(signedURLResponse, file);
        await this.fileUploadService.uploadFile(
          signedURLResponse.upload_data.url,
          fileUploadPayload,
          uploadProgressHandler
        );
        await this.updateProjectAssetUploadStatus(projectId, signedURLResponse.asset_id);
        return signedURLResponse;
      })
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteNewAsset(assetPath: string): Promise<void> {
    return this.delete(assetPath)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteOldWorkspaceAsset(src: string): Promise<any> {
    const assetKey = getAssetIdFromUrl(src);
    return this.delete(`/api/workspace/file-assets/${assetKey}/`)
      .then((response) => response?.status)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async restoreNewAsset(src: string): Promise<void> {
    // remove the last slash and get the asset id
    const assetId = getAssetIdFromUrl(src);
    return this.post(`/api/assets/v2/workspace/restore/${assetId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async checkIfAssetExists(assetId: string): Promise<{
    exists: boolean;
  }> {
    return this.get(`/api/assets/v2/workspace/check/${assetId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async restoreOldEditorAsset(src: string): Promise<void> {
    const assetKey = getAssetIdFromUrl(src);
    return this.post(`/api/workspace/file-assets/${assetKey}/restore/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  cancelUpload() {
    this.cancelSource.cancel("Upload canceled");
  }

  async getUnsplashImages(query?: string): Promise<UnSplashImage[]> {
    return this.get(`/api/unsplash/`, {
      params: {
        query,
      },
    })
      .then((res) => res?.data?.results ?? res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async duplicateAsset(
    assetId: string,
    data: {
      entity_id?: string;
      entity_type: EFileAssetType;
      project_id?: string;
    }
  ): Promise<{ asset_id: string }> {
    return this.post(`/api/assets/v2/workspace/duplicate-assets/${assetId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
