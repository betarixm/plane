/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { EProductSubscriptionEnum } from "@plane/types";

/**
 * ===========================================================================
 * Event Groups
 * ===========================================================================
 */
export const GROUP_WORKSPACE_TRACKER_EVENT = "workspace_metrics";
export const GITHUB_REDIRECTED_TRACKER_EVENT = "github_redirected";
export const HEADER_GITHUB_ICON = "header_github_icon";

/**
 * ===========================================================================
 * Command palette tracker
 * ===========================================================================
 */
export const COMMAND_PALETTE_TRACKER_ELEMENTS = {
  COMMAND_PALETTE_SHORTCUT_KEY: "command_palette_shortcut_key",
};

/**
 * ===========================================================================
 * Workspace Events and Elements
 * ===========================================================================
 */
export const WORKSPACE_TRACKER_EVENTS = {
  update: "workspace_updated",
};

export const WORKSPACE_TRACKER_ELEMENTS = {
  UPDATE_WORKSPACE_BUTTON: "update_workspace_button",
};

/**
 * ===========================================================================
 * Project Events and Elements
 * ===========================================================================
 */
export const PROJECT_TRACKER_EVENTS = {
  create: "project_created",
  update: "project_updated",
  delete: "project_deleted",
  feature_toggled: "feature_toggled",
};

export const PROJECT_TRACKER_ELEMENTS = {
  EXTENDED_SIDEBAR_ADD_BUTTON: "extended_sidebar_add_project_button",
  SIDEBAR_CREATE_PROJECT_BUTTON: "sidebar_create_project_button",
  SIDEBAR_CREATE_PROJECT_TOOLTIP: "sidebar_create_project_tooltip",
  COMMAND_PALETTE_CREATE_BUTTON: "command_palette_create_project_button",
  COMMAND_PALETTE_SHORTCUT_CREATE_BUTTON: "command_palette_shortcut_create_project_button",
  EMPTY_STATE_CREATE_PROJECT_BUTTON: "empty_state_create_project_button",
  CREATE_HEADER_BUTTON: "create_project_header_button",
  CREATE_FIRST_PROJECT_BUTTON: "create_first_project_button",
  DELETE_PROJECT_BUTTON: "delete_project_button",
  UPDATE_PROJECT_BUTTON: "update_project_button",
  CREATE_PROJECT_JIRA_IMPORT_DETAIL_PAGE: "create_project_jira_import_detail_page",
  TOGGLE_FEATURE: "toggle_project_feature",
};

/**
 * ===========================================================================
 * Cycle Events and Elements
 * ===========================================================================
 */
export const CYCLE_TRACKER_EVENTS = {
  create: "cycle_created",
  update: "cycle_updated",
  delete: "cycle_deleted",
  favorite: "cycle_favorited",
  unfavorite: "cycle_unfavorited",
  archive: "cycle_archived",
  restore: "cycle_restored",
};

export const CYCLE_TRACKER_ELEMENTS = {
  RIGHT_HEADER_ADD_BUTTON: "right_header_add_cycle_button",
  EMPTY_STATE_ADD_BUTTON: "empty_state_add_cycle_button",
  COMMAND_PALETTE_ADD_ITEM: "command_palette_add_cycle_item",
  RIGHT_SIDEBAR: "cycle_right_sidebar",
  QUICK_ACTIONS: "cycle_quick_actions",
  CONTEXT_MENU: "cycle_context_menu",
  LIST_ITEM: "cycle_list_item",
} as const;

/**
 * ===========================================================================
 * Module Events and Elements
 * ===========================================================================
 */
export const MODULE_TRACKER_EVENTS = {
  create: "module_created",
  update: "module_updated",
  delete: "module_deleted",
  favorite: "module_favorited",
  unfavorite: "module_unfavorited",
  archive: "module_archived",
  restore: "module_restored",
  link: {
    create: "module_link_created",
    update: "module_link_updated",
    delete: "module_link_deleted",
  },
};

export const MODULE_TRACKER_ELEMENTS = {
  RIGHT_HEADER_ADD_BUTTON: "right_header_add_module_button",
  EMPTY_STATE_ADD_BUTTON: "empty_state_add_module_button",
  COMMAND_PALETTE_ADD_ITEM: "command_palette_add_module_item",
  RIGHT_SIDEBAR: "module_right_sidebar",
  QUICK_ACTIONS: "module_quick_actions",
  CONTEXT_MENU: "module_context_menu",
  LIST_ITEM: "module_list_item",
  CARD_ITEM: "module_card_item",
} as const;

/**
 * ===========================================================================
 * Work Item Events and Elements
 * ===========================================================================
 */
export const WORK_ITEM_TRACKER_EVENTS = {
  create: "work_item_created",
  add_existing: "work_item_add_existing",
  update: "work_item_updated",
  delete: "work_item_deleted",
  archive: "work_item_archived",
  restore: "work_item_restored",
  attachment: {
    add: "work_item_attachment_added",
    remove: "work_item_attachment_removed",
  },
  sub_issue: {
    update: "sub_issue_updated",
    remove: "sub_issue_removed",
    delete: "sub_issue_deleted",
    create: "sub_issue_created",
    add_existing: "sub_issue_add_existing",
  },
  draft: {
    create: "draft_work_item_created",
  },
};
export const WORK_ITEM_TRACKER_ELEMENTS = {
  HEADER_ADD_BUTTON: {
    WORK_ITEMS: "work_items_header_add_work_item_button",
    PROJECT_VIEW: "project_view_header_add_work_item_button",
    CYCLE: "cycle_header_add_work_item_button",
    MODULE: "module_header_add_work_item_button",
  },
  COMMAND_PALETTE_ADD_BUTTON: "command_palette_add_work_item_button",
  EMPTY_STATE_ADD_BUTTON: {
    WORK_ITEMS: "work_items_empty_state_add_work_item_button",
    PROJECT_VIEW: "project_view_empty_state_add_work_item_button",
    CYCLE: "cycle_empty_state_add_work_item_button",
    MODULE: "module_empty_state_add_work_item_button",
    GLOBAL_VIEW: "global_view_empty_state_add_work_item_button",
  },
  QUICK_ACTIONS: {
    WORK_ITEMS: "work_items_quick_actions",
    PROJECT_VIEW: "project_view_work_items_quick_actions",
    CYCLE: "cycle_work_items_quick_actions",
    MODULE: "module_work_items_quick_actions",
    GLOBAL_VIEW: "global_view_work_items_quick_actions",
    ARCHIVED: "archived_work_items_quick_actions",
    DRAFT: "draft_work_items_quick_actions",
  },
  CONTEXT_MENU: {
    WORK_ITEMS: "work_items_context_menu",
    PROJECT_VIEW: "project_view_context_menu",
    CYCLE: "cycle_context_menu",
    MODULE: "module_context_menu",
    GLOBAL_VIEW: "global_view_context_menu",
    ARCHIVED: "archived_context_menu",
    DRAFT: "draft_context_menu",
  },
} as const;

/**
 * ===========================================================================
 * State Events and Elements
 * ===========================================================================
 */
export const STATE_TRACKER_EVENTS = {
  create: "state_created",
  update: "state_updated",
  delete: "state_deleted",
};
export const STATE_TRACKER_ELEMENTS = {
  STATE_GROUP_ADD_BUTTON: "state_group_add_button",
  STATE_LIST_DELETE_BUTTON: "state_list_delete_button",
  STATE_LIST_EDIT_BUTTON: "state_list_edit_button",
};

/**
 * ===========================================================================
 * Member Events and Elements
 * ===========================================================================
 */
export const MEMBER_TRACKER_EVENTS = {
  project: {
    add: "project_member_added",
    leave: "project_member_left",
  },
};
export const MEMBER_TRACKER_ELEMENTS = {
  HEADER_ADD_BUTTON: "header_add_member_button",
  SIDEBAR_PROJECT_QUICK_ACTIONS: "sidebar_project_quick_actions",
  PROJECT_MEMBER_TABLE_CONTEXT_MENU: "project_member_table_context_menu",
} as const;

/**
 * ===========================================================================
 * Global View Events and Elements
 * ===========================================================================
 */
export const GLOBAL_VIEW_TRACKER_EVENTS = {
  create: "global_view_created",
  update: "global_view_updated",
  delete: "global_view_deleted",
  open: "global_view_opened",
};

export const GLOBAL_VIEW_TRACKER_ELEMENTS = {
  RIGHT_HEADER_ADD_BUTTON: "global_view_right_header_add_button",
  HEADER_SAVE_VIEW_BUTTON: "global_view_header_save_view_button",
  QUICK_ACTIONS: "global_view_quick_actions",
  LIST_ITEM: "global_view_list_item",
};

/**
 * ===========================================================================
 * Project View Events and Elements
 * ===========================================================================
 */
export const PROJECT_VIEW_TRACKER_EVENTS = {
  create: "project_view_created",
  update: "project_view_updated",
  delete: "project_view_deleted",
};

export const PROJECT_VIEW_TRACKER_ELEMENTS = {
  RIGHT_HEADER_ADD_BUTTON: "project_view_right_header_add_button",
  COMMAND_PALETTE_ADD_ITEM: "command_palette_add_project_view_item",
  EMPTY_STATE_CREATE_BUTTON: "project_view_empty_state_create_button",
  HEADER_SAVE_VIEW_BUTTON: "project_view_header_save_view_button",
  PROJECT_HEADER_SAVE_AS_VIEW_BUTTON: "project_view_header_save_as_view_button",
  CYCLE_HEADER_SAVE_AS_VIEW_BUTTON: "cycle_header_save_as_view_button",
  MODULE_HEADER_SAVE_AS_VIEW_BUTTON: "module_header_save_as_view_button",
  QUICK_ACTIONS: "project_view_quick_actions",
  LIST_ITEM_CONTEXT_MENU: "project_view_list_item_context_menu",
};

/**
 * ===========================================================================
 * Notification Events and Elements
 * ===========================================================================
 */
export const NOTIFICATION_TRACKER_EVENTS = {
  archive: "notification_archived",
  unarchive: "notification_unarchived",
  mark_read: "notification_marked_read",
  mark_unread: "notification_marked_unread",
  all_marked_read: "all_notifications_marked_read",
};

export const NOTIFICATION_TRACKER_ELEMENTS = {
  MARK_ALL_AS_READ_BUTTON: "mark_all_as_read_button",
  ARCHIVE_UNARCHIVE_BUTTON: "archive_unarchive_button",
  MARK_READ_UNREAD_BUTTON: "mark_read_unread_button",
};

/**
 * ===========================================================================
 * User Events
 * ===========================================================================
 */
export const USER_TRACKER_ELEMENTS = {
  CHANGELOG_REDIRECTED: "changelog_redirected",
};

/**
 * ===========================================================================
 * Sidebar Events
 * ===========================================================================
 */
export const SIDEBAR_TRACKER_ELEMENTS = {
  USER_MENU_ITEM: "sidenav_user_menu_item",
  CREATE_WORK_ITEM_BUTTON: "sidebar_create_work_item_button",
};

/**
 * ===========================================================================
 * Project Settings Events and Elements
 * ===========================================================================
 */
export const PROJECT_SETTINGS_TRACKER_ELEMENTS = {
  LABELS_EMPTY_STATE_CREATE_BUTTON: "labels_empty_state_create_button",
  LABELS_HEADER_CREATE_BUTTON: "labels_header_create_button",
  LABELS_CONTEXT_MENU: "labels_context_menu",
  LABELS_DELETE_BUTTON: "labels_delete_button",
  ESTIMATES_TOGGLE_BUTTON: "estimates_toggle_button",
  ESTIMATES_EMPTY_STATE_CREATE_BUTTON: "estimates_empty_state_create_button",
  ESTIMATES_LIST_ITEM: "estimates_list_item",
  AUTOMATIONS_ARCHIVE_TOGGLE_BUTTON: "automations_archive_toggle_button",
  AUTOMATIONS_CLOSE_TOGGLE_BUTTON: "automations_close_toggle_button",
};

export const PROJECT_SETTINGS_TRACKER_EVENTS = {
  // labels
  label_created: "label_created",
  label_updated: "label_updated",
  label_deleted: "label_deleted",
  // estimates
  estimate_created: "estimate_created",
  estimate_updated: "estimate_updated",
  estimate_deleted: "estimate_deleted",
  estimates_toggle: "estimates_toggled",
  // automations
  auto_close_workitems: "auto_close_workitems",
  auto_archive_workitems: "auto_archive_workitems",
};

export const PROFILE_SETTINGS_TRACKER_ELEMENTS = {
  LIST_ITEM_DELETE_ICON: "list_item_delete_icon",
};

/**
 * ===========================================================================
 * Workspace Settings Events and Elements
 * ===========================================================================
 */
export const WORKSPACE_SETTINGS_TRACKER_EVENTS = {
  // Billing
  upgrade_plan_redirected: "upgrade_plan_redirected",
  // Exports
  csv_exported: "csv_exported",
  // Webhooks
  webhook_created: "webhook_created",
  webhook_deleted: "webhook_deleted",
  webhook_toggled: "webhook_toggled",
  webhook_details_page_toggled: "webhook_details_page_toggled",
  webhook_updated: "webhook_updated",
};

export const WORKSPACE_SETTINGS_TRACKER_ELEMENTS = {
  // Billing
  BILLING_UPGRADE_BUTTON: (subscriptionType: EProductSubscriptionEnum) => `billing_upgrade_${subscriptionType}_button`,
  BILLING_TALK_TO_SALES_BUTTON: "billing_talk_to_sales_button",
  // Exports
  EXPORT_BUTTON: "export_button",
  // Webhooks
  HEADER_ADD_WEBHOOK_BUTTON: "header_add_webhook_button",
  EMPTY_STATE_ADD_WEBHOOK_BUTTON: "empty_state_add_webhook_button",
  LIST_ITEM_DELETE_BUTTON: "list_item_delete_button",
  WEBHOOK_LIST_ITEM_TOGGLE_SWITCH: "webhook_list_item_toggle_switch",
  WEBHOOK_DETAILS_PAGE_TOGGLE_SWITCH: "webhook_details_page_toggle_switch",
  WEBHOOK_DELETE_BUTTON: "webhook_delete_button",
  WEBHOOK_UPDATE_BUTTON: "webhook_update_button",
};
