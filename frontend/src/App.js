// import logo from './logo.svg';
import styles from './styles/App.module.css';
// import SemiCircularProgressBar from './Components/SemiCircularProgressBar'; //DELETE

import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Dashboard from './pages/Dashboard';
// not yet ready
// import Pipeline from './pages/Pipeline';
// import Debug from './pages/Debug';
import MenuBar from './Components/MenuBar.js';

console.log('Imported styles:', styles);

function App() {
  return (
    <Router>
      <div className={styles.App}>
        <div className={styles.menu}>
          <MenuBar />
        </div>

        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          {/* <Route path="/pipeline" element={<Pipeline />} /> */}
          {/* <Route path="/debug/:id" element={<Debug />} /> */}
        </Routes>
      </div>
    </Router>
  );
  
}


export default App;
