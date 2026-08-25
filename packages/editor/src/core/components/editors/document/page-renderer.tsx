/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Editor } from "@tiptap/react";
// plane imports
import { cn } from "@plane/utils";
// components
import { DocumentContentLoader, EditorContainer, EditorContentWrapper } from "@/components/editors";
import { BlockMenu, EditorBubbleMenu } from "@/components/menus";
// types
import type { IEditorProps, IEditorPropsExtended, TAIHandler, TDisplayConfig } from "@/types";

type Props = {
  aiHandler?: TAIHandler;
  bubbleMenuEnabled: boolean;
  disabledExtensions: IEditorProps["disabledExtensions"];
  displayConfig: TDisplayConfig;
  documentLoaderClassName?: string;
  editor: Editor;
  editorContainerClassName: string;
  extendedEditorProps: IEditorPropsExtended;
  flaggedExtensions: IEditorProps["flaggedExtensions"];
  id: string;
  isLoading?: boolean;
  isTouchDevice: boolean;
  tabIndex?: number;
};

export function PageRenderer(props: Props) {
  const {
    bubbleMenuEnabled,
    disabledExtensions,
    displayConfig,
    documentLoaderClassName,
    editor,
    editorContainerClassName,
    extendedEditorProps,
    flaggedExtensions,
    id,
    isLoading,
    isTouchDevice,
    tabIndex,
  } = props;
  return (
    <div
      className={cn("frame-renderer w-full flex-grow", {
        "wide-layout": displayConfig.wideLayout,
      })}
    >
      {isLoading ? (
        <DocumentContentLoader className={documentLoaderClassName} />
      ) : (
        <>
          <EditorContainer
            displayConfig={displayConfig}
            editor={editor}
            editorContainerClassName={editorContainerClassName}
            id={id}
            isTouchDevice={isTouchDevice}
          >
            <EditorContentWrapper editor={editor} id={id} tabIndex={tabIndex} />
            {editor.isEditable && !isTouchDevice && (
              <div>
                {bubbleMenuEnabled && (
                  <EditorBubbleMenu
                    editor={editor}
                    disabledExtensions={disabledExtensions}
                    extendedEditorProps={extendedEditorProps}
                    flaggedExtensions={flaggedExtensions}
                  />
                )}
                <BlockMenu
                  editor={editor}
                  flaggedExtensions={flaggedExtensions}
                  disabledExtensions={disabledExtensions}
                />
              </div>
            )}
          </EditorContainer>
        </>
      )}
    </div>
  );
}
