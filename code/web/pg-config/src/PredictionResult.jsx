import React from "react";

export default function PredictionResult({ prediction }) {
  // Early return if no prediction or prediction is empty
  if (!prediction || Object.keys(prediction).length === 0) {
    return null;
  }

  // Safely destructure with fallbacks
  const { postgres_disk_io_prediction = {}, metadata = {} } = prediction;
  const { database = "", tablespace = "", files = [] } = postgres_disk_io_prediction;
  const { units = { size: "MB", throughput: "MB/s" }, notes = [] } = metadata;

  // Early return if essential data is missing
  if (!files.length) {
    return (
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-700 mb-3">Disk I/O Prediction Results</h2>
        <div className="text-gray-600">No prediction data available</div>
      </section>
    );
  }

  return (
    <section className="mb-8">
      <h2 className="text-xl font-semibold text-gray-700 mb-3">Disk I/O Prediction Results</h2>
      <div className="mb-2 text-gray-600">
        {database && <><b>Database:</b> {database} &nbsp;</>}
        {tablespace && <><b>Tablespace:</b> {tablespace}</>}
      </div>
      <table className="min-w-full bg-white border mb-4">
        <thead>
          <tr>
            <th className="border px-4 py-2">File Name</th>
            <th className="border px-4 py-2">Type</th>
            <th className="border px-4 py-2">Size ({units.size})</th>
            <th className="border px-4 py-2">Scenario (Cache Hit Ratio)</th>
            <th className="border px-4 py-2">Read Ops</th>
            <th className="border px-4 py-2">Write Ops</th>
            <th className="border px-4 py-2">Read BW ({units.throughput})</th>
            <th className="border px-4 py-2">Write BW ({units.throughput})</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file, fidx) => (
            file.access_pattern?.io_scenarios?.map((scenario, sidx) => (
              <tr key={`${fidx}-${sidx}`} className="border">
                {sidx === 0 && (
                  <>
                    <td className="border px-4 py-2" rowSpan={file.access_pattern.io_scenarios.length}>
                      {file.name}
                    </td>
                    <td className="border px-4 py-2" rowSpan={file.access_pattern.io_scenarios.length}>
                      {file.type}
                    </td>
                    <td className="border px-4 py-2" rowSpan={file.access_pattern.io_scenarios.length}>
                      {file.estimated_size_mb}
                    </td>
                  </>
                )}
                <td className="border px-4 py-2">{scenario.cache_hit_ratio}</td>
                <td className="border px-4 py-2">{scenario.read_ops}</td>
                <td className="border px-4 py-2">{scenario.write_ops}</td>
                <td className="border px-4 py-2">{scenario.read_throughput_mb_s}</td>
                <td className="border px-4 py-2">{scenario.write_throughput_mb_s}</td>
              </tr>
            ))
          ))}
        </tbody>
      </table>
      {notes.length > 0 && (
        <div className="text-sm text-gray-500 space-y-1 mb-2">
          {notes.map((note, i) => <div key={i}>• {note}</div>)}
        </div>
      )}
    </section>
  );
}
