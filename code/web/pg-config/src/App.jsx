import React, { useState, useEffect } from "react";
import Papa from "papaparse";
import hintsCSV from "./postgres_config_hints.csv?raw";
import './App.css';

export default function App() {
  const [tables, setTables] = useState([{ name: "", ddl: "", row_count: "" }]);
  const [query, setQuery] = useState("");

  const ON_OFF_FIELDS = ["fsync", "autovacuum", "wal_compression", "synchronous_commit"];
  const TIME_FIELDS = [
    "checkpoint_timeout",
    "wal_writer_delay",
    "autovacuum_naptime",
    "autovacuum_vacuum_cost_delay"
  ];
  const BYTES_FIELDS = [
    "shared_buffers",
    "work_mem",
    "maintenance_work_mem",
    "wal_buffers",
    "max_wal_size",
    "min_wal_size",
    "temp_buffers",
    "effective_cache_size"
  ];

  const TIME_UNITS = ["ms", "s", "min", "h"];
  const SIZE_UNITS = ["KB", "MB", "GB"];

  const [config, setConfig] = useState({
    shared_buffers: "4GB",
    effective_cache_size: "12GB",
    work_mem: "4MB",
    maintenance_work_mem: "64MB",
    wal_buffers: "-1",
    max_wal_size: "1GB",
    min_wal_size: "80MB",
    checkpoint_timeout: "5min",
    checkpoint_completion_target: "0.9",
    wal_compression: "on",
    wal_writer_delay: "200ms",
    wal_level: "replica",
    fsync: "on",
    synchronous_commit: "on",
    random_page_cost: "4.0",
    seq_page_cost: "1.0",
    temp_buffers: "8MB",
    autovacuum: "on",
    autovacuum_max_workers: "3",
    autovacuum_naptime: "1min",
    autovacuum_vacuum_cost_limit: "200",
    autovacuum_vacuum_cost_delay: "20ms",
  });
  const [hints, setHints] = useState({});

  useEffect(() => {
    Papa.parse(hintsCSV, {
      header: true,
      skipEmptyLines: true,
      complete: (result) => {
        const hintObj = {};
        result.data.forEach((row) => {
          hintObj[row.key] = row.hint;
        });
        setHints(hintObj);
      },
    });
  }, []);

  const addTable = () => {
    setTables([...tables, { name: "", ddl: "", row_count: "" }]);
  };

  const handleTableChange = (index, field, value) => {
    const updated = [...tables];
    updated[index][field] = value;
    setTables(updated);
  };

  const handleConfigChange = (key, value) => {
    setConfig({ ...config, [key]: value });
  };

  function parseValueUnit(value, units) {
    const match = value.match(/^(\d+)([a-zA-Z]*)$/);
    if (!match) return { number: "", unit: units[0] };
    const [, number, unit] = match;
    return {
      number,
      unit: units.includes(unit) ? unit : units[0]
    };
  }

  return (
    <div className="bg-gray-100 min-h-screen p-6">
      <div className="max-w-5xl mx-auto bg-white shadow-xl rounded-lg overflow-hidden">
        <div className="px-6 py-8">
          <h1 className="text-3xl font-extrabold text-gray-800 mb-4">
            Load Prediction Configurator
          </h1>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-700 mb-3">Tables</h2>
            {tables.map((table, index) => (
              <div
                key={index}
                className="bg-gray-50 rounded-md shadow-sm p-4 mb-4"
              >
                <div className="mb-2">
                  <label
                    htmlFor={`table-name-${index}`}
                    className="block text-sm font-medium text-gray-600"
                  >
                    Table Name
                  </label>
                  <input
                    type="text"
                    id={`table-name-${index}`}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    value={table.name}
                    onChange={(e) =>
                      handleTableChange(index, "name", e.target.value)
                    }
                  />
                </div>
                <div className="mb-2">
                  <label
                    htmlFor={`table-ddl-${index}`}
                    className="block text-sm font-medium text-gray-600"
                  >
                    DDL
                  </label>
                  <textarea
                    id={`table-ddl-${index}`}
                    rows={4}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    value={table.ddl}
                    onChange={(e) =>
                      handleTableChange(index, "ddl", e.target.value)
                    }
                  />
                </div>
                <div>
                  <label
                    htmlFor={`table-row-count-${index}`}
                    className="block text-sm font-medium text-gray-600"
                  >
                    Row Count
                  </label>
                  <input
                    type="number"
                    id={`table-row-count-${index}`}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    value={table.row_count}
                    onChange={(e) =>
                      handleTableChange(index, "row_count", e.target.value)
                    }
                  />
                </div>
              </div>
            ))}
            <button
              onClick={addTable}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded shadow focus:outline-none focus:shadow-outline"
            >
              + Add Table
            </button>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-700 mb-3">
              PostgreSQL Configuration
            </h2>
            <div className="config-grid">
              {Object.entries(config).map(([key, value]) => {
                // On/Off поля
                if (ON_OFF_FIELDS.includes(key)) {
                  return (
                    <div key={key} className="mb-4">
                      <label htmlFor={`config-${key}`} className="block text-sm font-medium text-gray-600">
                        {key}
                      </label>
                      <select
                        id={`config-${key}`}
                        value={value}
                        onChange={e => handleConfigChange(key, e.target.value)}
                        className="large-select"
                      >
                        <option value="on">on</option>
                        <option value="off">off</option>
                      </select>
                      {hints[key] && <p className="mt-1 text-sm text-gray-500">{hints[key]}</p>}
                    </div>
                  );
                }

                // Временные поля
                if (TIME_FIELDS.includes(key)) {
                  const { number, unit } = parseValueUnit(value, TIME_UNITS);
                  return (
                    <div key={key} className="mb-4">
                      <label htmlFor={`config-${key}`} className="block text-sm font-medium text-gray-600">{key}</label>
                      <div className="flex gap-2">
                        <input
                          type="number"
                          id={`config-${key}-number`}
                          value={number}
                          min={0}
                          className="mt-1 block w-2/3 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                          onChange={e => handleConfigChange(key, e.target.value + unit)}
                        />
                        <select
                          id={`config-${key}-unit`}
                          value={unit}
                          className="mt-1 block w-1/3 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                          onChange={e => handleConfigChange(key, number + e.target.value)}
                        >
                          {TIME_UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                        </select>
                      </div>
                      {hints[key] && <p className="mt-1 text-sm text-gray-500">{hints[key]}</p>}
                    </div>
                  );
                }

                // Байтовые поля
                if (BYTES_FIELDS.includes(key)) {
                  const { number, unit } = parseValueUnit(value, SIZE_UNITS);
                  return (
                    <div key={key} className="mb-4">
                      <label htmlFor={`config-${key}`} className="block text-sm font-medium text-gray-600">{key}</label>
                      <div className="input-unit-row">
                        <input
                          type="number"
                          id={`config-${key}-number`}
                          value={number}
                          min={0}
                           className="input-half"
                          onChange={e => handleConfigChange(key, e.target.value + unit)}
                        />
                        <select
                          id={`config-${key}-unit`}
                          value={unit}
                           className="input-half"
                           onChange={e => handleConfigChange(key, number + e.target.value)}
                        >
                          {SIZE_UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                        </select>
                      </div>
                      {hints[key] && <p className="mt-1 text-sm text-gray-500">{hints[key]}</p>}
                    </div>
                  );
                }

                // Дефолтное текстовое поле
                return (
                  <div key={key} className="mb-4">
                    <label htmlFor={`config-${key}`} className="block text-sm font-medium text-gray-600">{key}</label>
                    <input
                      type="text"
                      id={`config-${key}`}
                      title={hints[key] || ""}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      value={value}
                      onChange={e => handleConfigChange(key, e.target.value)}
                    />
                    {hints[key] && <p className="mt-1 text-sm text-gray-500">{hints[key]}</p>}
                  </div>
                );
              })}
            </div>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-700 mb-3">Query</h2>
            <textarea
              rows={6}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </section>

          <button className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded shadow focus:outline-none focus:shadow-outline">
            Submit
          </button>
        </div>
      </div>
    </div>
  );
}