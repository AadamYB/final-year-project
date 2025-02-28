// import logo from './logo.svg';
import styles from './styles/App.module.css';
import SemiCircularProgressBar from './Components/SemiCircularProgressBar';

console.log('Imported styles:', styles);

function App() {
  return (
    <div className={styles.App}>
      {/* <header className={styles.Appheader}>
        <img src={logo} className={styles.Applogo} alt="logo" />
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className={styles.Applink}
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React today
        </a>
      </header> */} 
      <div className={styles.menu}>
        {/*Add menu details*/}
      </div>

      <div className={styles.section}>
        <div className={styles.container}>
          <div className={styles.progressBarContainer}>
            <h1>unit-tests</h1>
            <SemiCircularProgressBar value={5} gauge="Low" unit="mins" denominator="60"/>
          </div>
        </div>
        <div className={styles.container}>
          <div className={styles.progressBarContainer}>
            <h1>failure rate</h1>
            <SemiCircularProgressBar value={60} gauge="Moderate" unit="%" denominator="100"/>
          </div>
        </div>
        <div className={styles.container}>
          <div className={styles.progressBarContainer}>
            <h1>integration-tests</h1>
            <SemiCircularProgressBar value={90} gauge="High" unit="mins" denominator="100"/>
          </div>
        </div>
        <div className={styles.container}>
          <div className={styles.progressBarContainer}>
            <h1>lint</h1>
            <SemiCircularProgressBar value={11} gauge="Very High" unit="mins" denominator="12"/>
          </div>
        </div>
      </div>

      <div className={styles.section}>
         {/*Add pipeline details?*/}
      </div>
    </div>
  );
  
}


export default App;
