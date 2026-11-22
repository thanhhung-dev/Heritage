export type ActionType = 'Process' | 'Edit' | 'Upload' | 'Approve' | 'Request changes';

export type ActionResult =
  | 'Processing'
  | 'Failed'
  | 'Submitted'
  | 'Success'
  | 'Approved'
  | 'Changes requested'
  | 'Indexed';

export interface ActionHistoryItem {
  id: string;
  timestamp: string;
  actor: string;
  actorRole: string;
  actorEmail: string;
  action: ActionType;
  targetTitle: string;
  targetSubtitle: string;
  targetDetail: string;
  jobInfo: string;
  detailHeadline: string;
  detailDescription: string;
  result: ActionResult;
}

export interface ActionHistoryFilters {
  search: string;
  actor: string;
  action: string;
  dateRange: [string, string] | null;
  result: string;
}