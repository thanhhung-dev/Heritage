"use client";

import { useId, useState, type ReactNode } from "react";
import { DownOutlined, FilterOutlined } from "@ant-design/icons";
import { DESIGN_CATEGORIES } from "@/features/search/catalogue";
import { UNCATEGORIZED, type SearchFilterKey } from "@/features/search/search-params";
import type { SearchFacet, SearchLocationGroup, SearchState } from "@/features/search/types";
import styles from "@/features/search/search.module.css";

interface SearchFiltersProps {
  state: SearchState;
  categories: SearchFacet[];
  groups: SearchLocationGroup[];
  loading: boolean;
  onToggle: (key: SearchFilterKey, value: string) => void;
}

function LocationGroup({ group, selectedSites, selected, onToggle, renderSite }: {
  group: SearchLocationGroup;
  selectedSites: string[];
  selected: boolean;
  onToggle: () => void;
  renderSite: (site: SearchFacet) => ReactNode;
}) {
  const [expanded, setExpanded] = useState(false);
  const sitesId = useId();
  // Keep the reference sidebar compact, but always expose selected shared-URL sites.
  const visible = expanded ? group.sites : group.sites.filter((site, index) => index < 3 || selectedSites.includes(site.value));
  return <div className={styles.locationGroup}>
    <label className={`${styles.filterChoice} ${styles.regionChoice}`}>
      <input type="checkbox" name="regions" value={group.value} checked={selected} onChange={onToggle} />
      <span>{group.label} <span>({group.count} {group.count === 1 ? "SITE" : "SITES"})</span></span>
    </label>
    <div className={styles.siteChoices} id={sitesId}>{visible.map(renderSite)}</div>
    {(expanded || visible.length < group.sites.length) && <button type="button" className={styles.moreSites}
      aria-expanded={expanded} aria-controls={sitesId} onClick={() => setExpanded(!expanded)}>
      {expanded ? "Show fewer sites" : `Show all ${group.sites.length} sites`}
    </button>}
  </div>;
}

export function SearchFilters({ state, categories, groups, loading, onToggle }: SearchFiltersProps) {
  const [expanded, setExpanded] = useState(false);
  const bodyId = useId();
  const count = state.regions.length + state.categories.length + state.locations.length;
  const categoryOptions = categories.length ? [...categories] : DESIGN_CATEGORIES.map((label) => ({ value: label, label, count: 0 }));
  for (const value of state.categories) if (!categoryOptions.some((item) => item.value === value)) categoryOptions.push({ value, label: value === UNCATEGORIZED ? "Uncategorized" : value, count: 0 });
  const knownRegions = new Set(groups.map((group) => group.value));
  const knownSites = new Set(groups.flatMap((group) => group.sites.map((site) => site.value)));
  const checkbox = (key: SearchFilterKey, option: SearchFacet) => <label key={option.value} className={styles.filterChoice}>
    <input type="checkbox" name={key} value={option.value} checked={state[key].includes(option.value)}
      disabled={loading || (!option.count && !state[key].includes(option.value))} onChange={() => onToggle(key, option.value)} />
    <span>{option.label}{!loading && <span className={styles.facetCount}> ({option.count})</span>}</span>
  </label>;
  return <aside className={styles.sidebar} aria-label="Filter tours">
    <button className={styles.filterToggle} type="button" aria-expanded={expanded} aria-controls={bodyId} onClick={() => setExpanded(!expanded)}>
      <FilterOutlined /> Filters{count > 0 && <span className={styles.filterCount}>{count}</span>}<DownOutlined />
    </button>
    <div className={styles.filtersBody} id={bodyId} data-expanded={expanded}>
      <fieldset className={styles.filterSection}>
        <legend>Category Selection</legend>
        {categoryOptions.map((option) => checkbox("categories", option))}
      </fieldset>
      <fieldset className={styles.filterSection}>
        <legend>Location Details</legend>
        {groups.map((group) => <LocationGroup key={group.value} group={group} selectedSites={state.locations}
          selected={state.regions.includes(group.value)} onToggle={() => onToggle("regions", group.value)}
          renderSite={(site) => checkbox("locations", site)} />)}
        {state.regions.filter((value) => !knownRegions.has(value)).map((value) => checkbox("regions", { value, label: value, count: 0 }))}
        {state.locations.filter((value) => !knownSites.has(value)).map((value) => checkbox("locations", { value, label: value, count: 0 }))}
        {loading && <div className={styles.filterSkeleton} aria-label="Loading locations"><i /><i /><i /><i /></div>}
        {!loading && !groups.length && <p className={styles.filterNote}>Locations will appear when tours are available.</p>}
      </fieldset>
    </div>
  </aside>;
}
