import React from "react";
import ScrapePanel from "../components/ScrapePanel";
import JobTable from "../components/JobTable";

/**
 * Discover screen — scrape panel at top, then the full filterable job table.
 * All data comes from the API via parent App component.
 */
export default function DiscoverView({ jobs, updateStatus, updateNotes, deleteJob, reload }) {
  return (
    <JobTable
      jobs={jobs}
      updateStatus={updateStatus}
      updateNotes={updateNotes}
      deleteJob={deleteJob}
      showUkToggle={true}
      headerSlot={<ScrapePanel reload={reload} />}
    />
  );
}