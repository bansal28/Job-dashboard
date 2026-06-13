import React from "react";
import ScrapePanel from "../components/ScrapePanel";
import SmartPicks from "../components/SmartPicks";
import JobTable from "../components/JobTable";
import DeadlineBanner from "../components/DeadlineBanner";

/**
 * Discover screen — Smart Picks + Scrape panel + filterable job table.
 */
export default function DiscoverView({ jobs, updateStatus, updateNotes, deleteJob, reload }) {
  return (
    <div>
      <div style={{ padding: "16px 24px 0" }}>
        <SmartPicks />
      </div>
      <DeadlineBanner />
      <JobTable
        jobs={jobs}
        updateStatus={updateStatus}
        updateNotes={updateNotes}
        deleteJob={deleteJob}
        showUkToggle={true}
        headerSlot={<ScrapePanel reload={reload} />}
      />
    </div>
  );
}
