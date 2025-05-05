// src/Components/NavigateToLastOrFirstBuild.js

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

const NavigateToLastOrFirstBuild = ({ target = "debug" }) => {
  const navigate = useNavigate();

  useEffect(() => {
    const redirectToBuild = async () => {
      const last = localStorage.getItem("lastBuildId");
      if (last) {
        navigate(`/${target}/${last}`);
        return;
      }

      try {
        const res = await fetch("http://35.177.242.182:5000/executions");
        const data = await res.json();
        if (data.length > 0) {
          navigate(`/${target}/${data[0].id}`);
        } else {
          navigate("/dashboard");
        }
      } catch (e) {
        console.error("❌ Could not fetch builds:", e);
        navigate("/dashboard");
      }
    };

    redirectToBuild();
  }, [navigate, target]);

  return <p>🔄 Redirecting to your most recent build...</p>;
};

export default NavigateToLastOrFirstBuild;