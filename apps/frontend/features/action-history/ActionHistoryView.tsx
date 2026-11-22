'use client';

import React, { useMemo, useState } from 'react';
import { FALLBACK_ACTION_HISTORY } from './fallbackActionHistoryData';
import {
  ActionHistoryFilters,
  ActionHistoryItem,
  ActionResult,
} from './types';
import styles from './ActionHistory.module.css';

const INITIAL_FILTERS: ActionHistoryFilters = {
  search: '',
  actor: 'All',
  action: 'All',
  dateRange: null,
  result: 'All',
};

const PAGE_SIZE = 10;

function formatUtcTimestamp(isoString: string): string {
  const date = new Date(isoString);
  const day = String(date.getUTCDate()).padStart(2, '0');
  const month = date.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' });
  const year = date.getUTCFullYear();
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');
  return `${day} ${month} ${year}, ${hours}:${minutes}`;
}

function getBadgeStyle(result: ActionResult): string {
  if (result === 'Failed') return `${styles.statusBadge} ${styles.statusFailed}`;
  if (result === 'Success' || result === 'Approved' || result === 'Indexed') {
    return `${styles.statusBadge} ${styles.statusSuccess}`;
  }
  if (result === 'Changes requested' || result === 'Processing') {
    return `${styles.statusBadge} ${styles.statusWarning}`;
  }
  return styles.statusBadge;
}

function formatActionOutcome(item: ActionHistoryItem): string {
  return `${item.action} ${item.result.toLowerCase()}`;
}

export default function ActionHistoryView() {
  const [filters, setFilters] = useState<ActionHistoryFilters>(INITIAL_FILTERS);
  const [logs, setLogs] = useState<ActionHistoryItem[]>(FALLBACK_ACTION_HISTORY);
  const [selectedEventId, setSelectedEventId] = useState<string>('EVT-209');
  const [currentPage, setCurrentPage] = useState<number>(1);

  const uniqueActors = useMemo(() => {
    return Array.from(new Set(logs.map((item) => item.actor)));
  }, [logs]);

  const filteredLogs = useMemo(() => {
    return logs.filter((item) => {
      const keyword = filters.search.trim().toLowerCase();
      const matchesSearch =
        !keyword ||
        item.targetTitle.toLowerCase().includes(keyword) ||
        item.targetSubtitle.toLowerCase().includes(keyword) ||
        item.id.toLowerCase().includes(keyword);

      const matchesActor =
        filters.actor === 'All' || item.actor === filters.actor;
      const matchesAction =
        filters.action === 'All' || item.action === filters.action;
      const matchesResult =
        filters.result === 'All' || item.result === filters.result;

      let matchesDate = true;
      if (filters.dateRange) {
        const [startDate, endDate] = filters.dateRange;
        const itemDate = item.timestamp.slice(0, 10);
        if (startDate && itemDate < startDate) matchesDate = false;
        if (endDate && itemDate > endDate) matchesDate = false;
      }

      return (
        matchesSearch &&
        matchesActor &&
        matchesAction &&
        matchesResult &&
        matchesDate
      );
    });
  }, [logs, filters]);

  const totalPages = Math.max(1, Math.ceil(filteredLogs.length / PAGE_SIZE));
  const safePage = Math.min(currentPage, totalPages);

  const paginatedLogs = useMemo(() => {
    const start = (safePage - 1) * PAGE_SIZE;
    return filteredLogs.slice(start, start + PAGE_SIZE);
  }, [filteredLogs, safePage]);

  const selectedEvent = useMemo(() => {
    return (
      filteredLogs.find((item) => item.id === selectedEventId) ||
      filteredLogs[0] ||
      null
    );
  }, [filteredLogs, selectedEventId]);

  const handleDateChange = (index: 0 | 1, value: string) => {
    setCurrentPage(1);
    setFilters((prev) => {
      const current: [string, string] = prev.dateRange
        ? [...prev.dateRange]
        : ['', ''];
      current[index] = value;
      return {
        ...prev,
        dateRange: current[0] || current[1] ? current : null,
      };
    });
  };

  return (
    <div className={styles.workspace}>
      {/* Header */}
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Activity log</h1>
          <p className={styles.subtitle}>
            Trace document uploads, edits, review decisions, and ingestion outcomes.
          </p>
        </div>
        <button
          type="button"
          className={styles.outlineBtn}
          onClick={() => {
            setLogs([...FALLBACK_ACTION_HISTORY]);
            setCurrentPage(1);
          }}
        >
          Refresh log
        </button>
      </div>

      {/* Demo data note */}
      <div className={styles.demoBar}>
        <span className={styles.demoLabel}>DEMO DATA</span>
        <span>
          Preview only · Illustrative records, not connected to a backend · 20 Oct 2026, 09:20 UTC · Source links use example.com
        </span>
      </div>

      {/* Filter Bar */}
      <div className={styles.filterRow}>
        <div className={styles.filterControls}>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search target or event..."
            value={filters.search}
            onChange={(e) => {
              setCurrentPage(1);
              setFilters((prev) => ({ ...prev, search: e.target.value }));
            }}
          />

          <select
            className={styles.selectInput}
            value={filters.actor}
            onChange={(e) => {
              setCurrentPage(1);
              setFilters((prev) => ({ ...prev, actor: e.target.value }));
            }}
          >
            <option value="All">Actor: All</option>
            {uniqueActors.map((actor) => (
              <option key={actor} value={actor}>
                Actor: {actor}
              </option>
            ))}
          </select>

          <select
            className={styles.selectInput}
            value={filters.action}
            onChange={(e) => {
              setCurrentPage(1);
              setFilters((prev) => ({ ...prev, action: e.target.value }));
            }}
          >
            <option value="All">Action: All</option>
            <option value="Process">Action: Process</option>
            <option value="Edit">Action: Edit</option>
            <option value="Upload">Action: Upload</option>
            <option value="Approve">Action: Approve</option>
            <option value="Request changes">Action: Request changes</option>
          </select>

          <div className={styles.dateGroup}>
            <input
              type="date"
              className={styles.dateInput}
              value={filters.dateRange?.[0] ?? ''}
              onChange={(e) => handleDateChange(0, e.target.value)}
              aria-label="Start date"
            />
            <span>–</span>
            <input
              type="date"
              className={styles.dateInput}
              value={filters.dateRange?.[1] ?? ''}
              onChange={(e) => handleDateChange(1, e.target.value)}
              aria-label="End date"
            />
          </div>

          <select
            className={styles.selectInput}
            value={filters.result}
            onChange={(e) => {
              setCurrentPage(1);
              setFilters((prev) => ({ ...prev, result: e.target.value }));
            }}
          >
            <option value="All">Result: All</option>
            <option value="Processing">Result: Processing</option>
            <option value="Failed">Result: Failed</option>
            <option value="Submitted">Result: Submitted</option>
            <option value="Success">Result: Success</option>
            <option value="Approved">Result: Approved</option>
            <option value="Changes requested">Result: Changes requested</option>
            <option value="Indexed">Result: Indexed</option>
          </select>
        </div>

        <button
          type="button"
          className={styles.outlineBtn}
          onClick={() => {
            setFilters(INITIAL_FILTERS);
            setCurrentPage(1);
          }}
        >
          Clear filters
        </button>
      </div>

      {/* Table */}
      <div className={styles.tableWrapper}>
        {paginatedLogs.length === 0 ? (
          <div className={styles.emptyState}>
            No action history records match the current filters.
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th style={{ width: 175 }}>Timestamp (UTC)</th>
                <th style={{ width: 140 }}>Actor</th>
                <th style={{ width: 145 }}>Action</th>
                <th>Target / context</th>
                <th style={{ width: 210, textAlign: 'left' }}>Result</th>
              </tr>
            </thead>
            <tbody>
              {paginatedLogs.map((item) => {
                const isSelected = selectedEvent?.id === item.id;
                return (
                  <tr
                    key={item.id}
                    className={isSelected ? styles.selectedRow : undefined}
                  >
                    <td className={styles.timestamp}>
                      {formatUtcTimestamp(item.timestamp)}
                    </td>
                    <td className={styles.actor}>{item.actor}</td>
                    <td className={styles.actionText}>{item.action}</td>
                    <td>
                      <div className={styles.targetTitle}>{item.targetTitle}</div>
                      <div className={styles.targetSub}>{item.targetSubtitle}</div>
                    </td>
                    <td>
                      <div className={styles.resultCell}>
                        <span className={getBadgeStyle(item.result)}>
                          {item.result}
                        </span>
                        <button
                          type="button"
                          className={styles.detailsBtn}
                          onClick={() => setSelectedEventId(item.id)}
                        >
                          Details
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination Footer */}
      <div className={styles.paginationBar}>
        <span>
          Showing {paginatedLogs.length} of {filteredLogs.length} events · Newest first
        </span>
        <div className={styles.paginationControls}>
          <span className={styles.pageIndicator}>
            Page {safePage} of {totalPages}
          </span>
          <button
            type="button"
            className={styles.pageBtn}
            disabled={safePage <= 1}
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </button>
          <button
            type="button"
            className={styles.pageBtn}
            disabled={safePage >= totalPages}
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
          >
            Next
          </button>
        </div>
      </div>

      {/* Event Details Card */}
      {selectedEvent && (
        <div className={styles.detailsCard}>
          <div className={styles.detailsHeader}>
            <h2 className={styles.detailsTitle}>Event details</h2>
            <p className={styles.detailsMeta}>
              Selected event · {selectedEvent.id} · {formatActionOutcome(selectedEvent)} ·{' '}
              {formatUtcTimestamp(selectedEvent.timestamp)} UTC
            </p>
          </div>

          <div className={styles.detailsGrid}>
            <div>
              <div className={styles.fieldLabel}>Actor</div>
              <div className={styles.fieldValue}>
                {selectedEvent.actor} · {selectedEvent.actorRole} · {selectedEvent.actorEmail}
              </div>
            </div>
            <div>
              <div className={styles.fieldLabel}>Target</div>
              <div className={styles.fieldValue}>{selectedEvent.targetDetail}</div>
            </div>
            <div>
              <div className={styles.fieldLabel}>Job</div>
              <div className={styles.fieldValue}>{selectedEvent.jobInfo}</div>
            </div>
          </div>

          <div className={styles.detailsFooter}>
            <div className={styles.detailsCopy}>
              <p className={styles.detailHeadline}>{selectedEvent.detailHeadline}</p>
              <p className={styles.detailDesc}>{selectedEvent.detailDescription}</p>
            </div>
            <div className={styles.detailsActions}>
              <button type="button" className={styles.outlineBtn}>
                View document
              </button>
              <button type="button" className={styles.outlineBtn}>
                View ingestion job
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}