// Helper component to redirect us to the last opened/first-in-list build when we click on another route in the menubar
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

const NavigateToLastOrFirstBuild = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const redirectToBuild = async () => {
      const last = localStorage.getItem("lastBuildId");
      if (last) {
        navigate(`/debug/${last}`);
        return;
      }

      try {
        const res = await fetch("http://35.177.242.182:5000/executions");
        const data = await res.json();
        if (data.length > 0) {
          navigate(`/debug/${data[0].id}`);
        } 
      } catch (e) {
        console.error("❌ Could not fetch builds:", e);
        navigate("/dashboard");
      }
    };

    redirectToBuild();
  }, [navigate]);

  return null;
};

export default NavigateToLastOrFirstBuild;