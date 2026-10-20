"use client";

import { ShareAltOutlined, LockOutlined } from "@ant-design/icons";
import { message } from "antd";
import type { MilestoneLevel } from "./types";
import styles from "./profile.module.css";

interface MilestonesTabProps {
  milestones: MilestoneLevel[];
}

/**
 * Share the current profile/milestones page link.
 * Prefers the native Web Share API (mobile browsers, some desktop browsers);
 * falls back to copying the URL to the clipboard when unavailable, and to a
 * `document.execCommand` copy when `navigator.clipboard` itself is missing
 * (older browsers / non-secure contexts).
 */
async function shareProgress(): Promise<void> {
  const shareUrl = window.location.href;
  const shareData = {
    title: "My Heritage exploration progress",
    text: "Check out my heritage exploration milestones!",
    url: shareUrl,
  };

  if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
    try {
      await navigator.share(shareData);
      return;
    } catch (err) {
      // AbortError = user cancelled the native share sheet; do nothing.
      if (err instanceof Error && err.name === "AbortError") return;
      // Any other failure falls through to the clipboard copy below.
    }
  }

  try {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(shareUrl);
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = shareUrl;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    message.success("Progress link copied to clipboard!");
  } catch {
    message.error("Could not copy the link. Please copy it manually from the address bar.");
  }
}

export function MilestonesTab({ milestones }: MilestonesTabProps) {
  return (
    <div>
      <div className={styles.milestonesHeader}>
        <div>
          <h2 className={styles.milestonesTitle}>Exploration Levels</h2>
          <p className={styles.milestonesSubtitle}>
            Reach 5 levels by discovering heritage, learning cultural stories, and exploring with your AI guide.
          </p>
        </div>
        <button type="button" className={styles.shareLink} onClick={shareProgress}>
          <ShareAltOutlined /> Share progress
        </button>
      </div>

      <div className={styles.levelsContainer}>
        {milestones.map((level, index) => {
          const totalTasks = level.tasks.length;
          const completedTasks = level.tasks.filter((task) => task.is_completed).length;
          const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
          const previousLevel = milestones[index - 1];
          const lockedHint = previousLevel ? `Unlock ${previousLevel.level_name} first` : undefined;

          return (
            <div
              key={level.id}
              className={[styles.levelCard, level.is_unlocked ? "" : styles.levelCardLocked].join(" ")}
              aria-disabled={!level.is_unlocked}
            >
              <div className={styles.levelHeader}>
                <div className={styles.levelInfo}>
                  <h3 className={styles.levelTitle}>
                    {!level.is_unlocked ? <LockOutlined className={styles.levelLockIcon} /> : null}
                    {level.level_name}
                  </h3>
                  <p className={styles.levelDescription}>{level.description}</p>
                </div>
                <span className={level.is_unlocked ? styles.levelStatus : styles.levelStatusLocked}>
                  {level.is_unlocked
                    ? `${completedTasks}/${totalTasks} tasks complete`
                    : lockedHint}
                </span>
              </div>

              <div className={styles.progressBar}>
                <div className={styles.progressFill} style={{ width: `${progressPercent}%` }} />
              </div>

              {level.is_unlocked ? (
                <div className={styles.tasksGrid}>
                  {level.tasks.map((task) => (
                    <div key={task.id} className={styles.taskItem}>
                      <span className={[styles.checkbox, task.is_completed ? styles.checked : ""].join(" ")} />
                      <span className={styles.taskLabel}>{task.title}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={styles.levelLockedOverlay}>
                  <LockOutlined /> {lockedHint}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className={styles.milestoneFooter}>
        <p className={styles.milestoneFooterText}>
          Keep exploring, each milestone celebrates a new step in your heritage journey.
        </p>
      </div>
    </div>
  );
}

