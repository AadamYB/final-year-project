// 📍 FRONTEND UPDATE - Add error chart with filters
import React, { useState, useEffect } from "react";
import styles from "../styles/Dashboard.module.css";
import Select from "react-select";
import SemiCircularProgressBar from "../Components/DashboardCards/ProgressBar/SemiCircularProgressBar";
import NumericCard from "../Components/DashboardCards/NumericCard/NumericCard";
import BuildCard from "../Components/DashboardCards/BuildCard/BuildCard";
import PipelineTable from "../Components/DashboardCards/tableCard/pipelineTable";

const Dashboard = () => {
  const [RepoName,  setRepoName] = useState("Repo Name");
  const [builds, setBuilds] = useState([]);
  const [pipelineTableData, setPipelineTableData] = useState([]);
  const [metrics, setMetrics] = useState({
    avg_build_time: 0,
    failure_rate: 0,
    active_builds: 0,
    pull_requests: 0,
    releases: 0,
  });
  const [errorChart, setErrorChart] = useState(null);
  const [selectedRange, setSelectedRange] = useState(null);

  const options = [
    { value: null, label: "Default" },
    { value: "15m", label: "Last 15 minutes" },
    { value: "1h", label: "Last 60 minutes" },
    { value: "3h", label: "Last 3 hours" },
    { value: "12h", label: "Last 12 hours" },
    { value: "1d", label: "Last 24 hours" },
    { value: "7d", label: "Last 7 days" },
  ];

  useEffect(() => {
    const fetchAllDashboardData = async () => {
      try {
        const buildUrl = new URL("http://35.177.242.182:5000/executions");
        const metricsUrl = new URL("http://35.177.242.182:5000/dashboard-metrics");
        const stagesUrl = new URL("http://35.177.242.182:5000/executions-with-stages");
  
        if (selectedRange) {
          buildUrl.searchParams.append("range", selectedRange);
          metricsUrl.searchParams.append("range", selectedRange);
          stagesUrl.searchParams.append("range", selectedRange);
        }
  
        const [buildsRes, metricsRes, stagesRes] = await Promise.all([
          fetch(buildUrl),
          fetch(metricsUrl),
          fetch(stagesUrl)
        ]);
  
        const buildsData = await buildsRes.json();
        const metricsData = await metricsRes.json();
        const stagesData = await stagesRes.json();
  
        setBuilds(buildsData);
        if (buildsData.length > 0) {
          setRepoName(buildsData[0].repo_title);
        }
  
        setMetrics(metricsData);
        setPipelineTableData(stagesData);
      } catch (err) {
        console.error("❌ Failed to fetch dashboard data:", err);
      }
    };
  
    fetchAllDashboardData();
  }, [selectedRange]);

  useEffect(() => {
    const fetchErrorChart = async () => {
      try {
        const url = new URL("http://35.177.242.182:5000/dashboard-error-chart");
        if (selectedRange) url.searchParams.append("range", selectedRange);
        const res = await fetch(url);
        const data = await res.json();
        setErrorChart(data.image);
      } catch (err) {
        console.error("❌ Failed to fetch error chart:", err);
      }
    };
    fetchErrorChart();
  }, [selectedRange]);

  useEffect(() => {
    const fetchPipelineTableData = async () => {
      try {
        const url = new URL("http://35.177.242.182:5000/executions-with-stages");
        if (selectedRange) url.searchParams.append("range", selectedRange);
        const res = await fetch(url);
        const data = await res.json();
        setPipelineTableData(data);
      } catch (err) {
        console.error("❌ Failed to fetch pipeline table data:", err);
      }
    };
  
    fetchPipelineTableData();
  }, [selectedRange]);

  return (
    <div className={styles.page}>
      <div className={styles.headerSection}>
        <h1>{RepoName}</h1>
          <Select
            className={styles.filter}
            options={options}
            placeholder="Filter"
            onChange={(selected) => setSelectedRange(selected.value)}
          />
      </div>

      <div className={styles.section}>
        <div className={styles.listContainer}>
          {builds.map((build) => (
            <BuildCard
              key={build.id}
              status={build.status}
              prName={build.pr_name}
              date={build.date}
              time={build.time}
            />
          ))}
        </div>

        <div className={styles.container}>
            <h1>Avg Build Time</h1>
            <SemiCircularProgressBar
              value={metrics.avg_build_time}
              gauge={
                metrics.avg_build_time <= 5
                  ? "Low"
                  : metrics.avg_build_time <= 15
                  ? "Moderate"
                  : "High"
              }
              unit="mins"
              denominator="60"
            />
        </div>

        <div className={styles.container}>
            <h1>Failure Rate</h1>
            <SemiCircularProgressBar
              value={metrics.failure_rate}
              gauge={
                metrics.failure_rate < 30
                  ? "Low"
                  : metrics.failure_rate < 60
                  ? "Moderate"
                  : "High"
              }
              unit="%"
              denominator="100"
            />
        </div>

        <div className={styles.container}>
          <NumericCard label="Active Builds" value={metrics.active_builds} />
        </div>

        <div className={styles.container}>
          <NumericCard label="Pull Requests" value={metrics.pull_requests} />
        </div>

        <div className={styles.container}>
          <NumericCard label="Releases" value={metrics.releases} />
        </div>

        <div className={styles.container}>
          <NumericCard label="Failed Builds" value={metrics.failed_builds} />
        </div>

        <div className={styles.container}>
          <NumericCard label="Passed Builds" value={metrics.passed_builds} />
        </div>

        <div className={styles.container}>
          <NumericCard label="Total Builds" value={metrics.total_builds} />
        </div>

      </div>

      <div className={styles.section2}>
        <div className={styles.pipelineContainer}>
          <PipelineTable builds={pipelineTableData} />
        </div>

        <div className={styles.barChartContainer}>
          {errorChart && <img src={`data:image/png;base64,${errorChart}`} alt="Error Chart" className={styles.errorChart} />}
        </div>
      </div>

    </div>
  );
};

export default Dashboard;