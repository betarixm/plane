/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export function AuthHeader() {
  return (
    <>
      <div className="flex flex-col gap-1">
        <span className="text-20 leading-7 font-semibold text-primary">Sign in to upvote or comment</span>
        <span className="text-20 leading-7 font-semibold text-placeholder">
          Contribute in nudging the features you want to get built.
        </span>
      </div>
    </>
  );
}
