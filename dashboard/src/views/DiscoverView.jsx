import React from "react";
import ScrapePanel from "../components/ScrapePanel";
import SmartPicks from "../components/SmartPicks";
import JobTable from "../components/JobTable";
import DeadlineBanner from "../components/DeadlineBanner";
import { T } from "../theme.jsx";

/**
 * Discover screen — Smart Picks + Scrape panel + filterable job table.
 */
export default function DiscoverView({ jobs, stats, updateStatus, updateNotes, deleteJob, reload }) {
  const reviewJobs = jobs.filter((job) => job.status === "New");

  return (
    <div>
      <div style={{ padding: "16px 24px 0" }}>
        <SmartPicks onApprove={(jobId) => updateStatus(jobId, "Approved")} />
        {stats?.total > jobs.length && (
          <div style={{ color: T.dim, fontSize: 11, marginBottom: 8 }}>
            Showing the ranked review queue: {reviewJobs.length.toLocaleString()} new jobs visible from {stats.total.toLocaleString()} stored jobs.
          </div>
        )}
      </div>
      <DeadlineBanner />
      <JobTable
        jobs={reviewJobs}
        updateStatus={updateStatus}
        updateNotes={updateNotes}
        deleteJob={deleteJob}
        showUkToggle={true}
        headerSlot={<ScrapePanel reload={reload} />}
      />
    </div>
  );
}
