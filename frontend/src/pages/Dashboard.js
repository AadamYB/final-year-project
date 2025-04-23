import React from "react";
import styles from "../styles/Dashboard.module.css";
import Select from "react-select";
import SemiCircularProgressBar from "../Components/DashboardCards/ProgressBar/SemiCircularProgressBar";
import NumericCard from "../Components/DashboardCards/NumericCard/NumericCard";
import BuildCard from "../Components/DashboardCards/BuildCard/BuildCard";

const Dashboard = ({ Repo_name }) => {

    const options = [
        {value: "fifteen-mins", label: "Last 15 minutes"},
        {value: "one-hour", label: "Last 60 minutes"},
        {value: "three-hours", label: "Last 3 hours"},
        {value: "twelve-hours", label: "Last 12 hours"},
        {value: "one-day", label: "Last 24 hours"},
        {value: "seven-days", label: "Last 7 days"},
    ];
  return (

    <div>
        <div className={styles.headerSection}>
            <h1>{Repo_name}</h1>
            <Select 
                className={styles.filter}
                options={options}
                placeholder="Filter"
            />
        </div>

        <div className={styles.section}>

            <div className={styles.listContainer}>
                <BuildCard status="Pending" prName="random name name" date="20/12/25" time="10:13"/>
                <BuildCard status="Passed" prName="random name name" date="20/12/25" time="10:13"/>
                <BuildCard status="Failed" prName="random name name" date="20/12/25" time="10:13"/>
                <BuildCard status="Passed" prName="random name name" date="20/12/25" time="10:13"/>
                <BuildCard status="Pending" prName="random name name" date="20/12/25" time="10:13"/>
                <BuildCard status="Passed" prName="random name name" date="20/12/25" time="10:13"/>
            </div>

            <div className={styles.container}>
                <div className={styles.progressBarContainer}>
                <h1>unit-tests</h1>
                <SemiCircularProgressBar 
                    value={5} 
                    gauge="Low" 
                    unit="mins" 
                    denominator="60" 
                />
                </div>
            </div>

            <div className={styles.container}>
                <div className={styles.progressBarContainer}>
                <h1>failure rate</h1>
                <SemiCircularProgressBar 
                    value={60} 
                    gauge="Moderate" 
                    unit="%" 
                    denominator="100" 
                />
                </div>
            </div>

            <div className={styles.container}>
                <div className={styles.progressBarContainer}>
                <h1>integration-tests</h1>
                <SemiCircularProgressBar 
                    value={90} 
                    gauge="High" 
                    unit="mins" 
                    denominator="100" 
                />
                </div>
            </div>

            <div className={styles.container}>
                <div className={styles.progressBarContainer}>
                <h1>lint</h1>
                <SemiCircularProgressBar 
                    value={11} 
                    gauge="Very High"
                    unit="mins" 
                    denominator="12" 
                />
                </div>
            </div>

            <div className={styles.container}>
                <div className={styles.progressBarContainer}>
                <h1>Avg Build Time</h1>
                <SemiCircularProgressBar 
                    value={17} 
                    gauge="Moderate"
                    unit="mins" 
                    denominator="33" 
                />
                </div>
            </div>

            <div className={styles.container}>
                <NumericCard 
                    label="Active Builds" 
                    value={5} 
                />
            </div>

            <div className={styles.container}>
                <NumericCard 
                    label="Releases" 
                    value={1} 
                />
            </div>

            <div className={styles.container}>
                <NumericCard 
                    label="Pull Requests" 
                    value={21} 
                />
            </div>

        </div>

        <div className={styles.section2}>
            <div className={styles.pipelineContainer}>

            </div>

            
            <div className={styles.barChartContainer}>

            </div>
        </div>
    </div>
  );
};

export default Dashboard;