import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import styles from "../styles/App.module.css";

const MenuBar = () => {
  const location = useLocation();
  const [debugTarget, setDebugTarget] = useState("/debug");

  useEffect(() => {
    const getTargetBuild = async () => {
      try {
        const res = await fetch("http://13.40.55.105:5000/executions");
        const builds = await res.json();

        const lastViewed = localStorage.getItem("lastBuildId");
        const isValid = builds.some((b) => b.id === lastViewed);
        const fallbackId = builds[0]?.id;
        const targetId = isValid ? lastViewed : fallbackId;

        if (targetId) {
          setDebugTarget(`/debug/${targetId}`);
        }
      } catch (err) {
        console.error("❌ MenuBar: Failed to fetch builds for redirect", err);
      }
    };

    getTargetBuild();
  }, []);

  const isActive = (path) => location.pathname.startsWith(path);

  const menuItems = [
    { name: "Debug", icon: "log.png", path: debugTarget },
    { name: "Pipeline", icon: "pipeline.png", path: "/pipeline" },
    { name: "Dashboard", icon: "dashboard.png", path: "/dashboard" },
    { name: "Account", icon: "user_1.png", path: "/user-details" },
  ];

  return (
    <nav className={styles.menuBar}>
      {menuItems.map((item) => (
        <Link
          key={item.name}
          to={item.path}
          className={`${styles.menuItem} ${isActive(item.path) ? styles.active : ""}`}
        >
          <img
            src={`${process.env.PUBLIC_URL}/icons/${item.icon}`}
            alt={`${item.name} icon`}
            className={styles.icon}
          />
        </Link>
      ))}
    </nav>
  );
};

export default MenuBar;