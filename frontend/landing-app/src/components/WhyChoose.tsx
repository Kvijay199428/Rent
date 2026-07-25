import { useState } from "react";
import { whyChooseFeatures, screenshotTabs } from "../data";

export default function WhyChoose() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <section className="why-section" id="benefits">
      <div className="why-grid">
        <div className="why-content">
          <div className="section-badge">Why Rent</div>
          <h2 className="section-title">Built for modern landlords</h2>
          <p className="section-subtitle" style={{ textAlign: "left" }}>
            Stop chasing payments and chasing paperwork. The platform automates
            the tedious parts of rent management so you can focus on what
            matters.
          </p>
          <ul className="benefits-list">
            {whyChooseFeatures.map((item) => (
              <li key={item}>
                <span className="check-icon">✓</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="why-preview">
          <div className="screenshot-tabs">
            {screenshotTabs.map((tab, i) => (
              <button
                key={tab}
                className={`screenshot-tab ${i === activeTab ? "active" : ""}`}
                onClick={() => setActiveTab(i)}
              >
                {tab}
              </button>
            ))}
          </div>
          <div className="screenshot-placeholder">
            <div className="screenshot-mockup">
              <div className="mockup-header">
                <span className="mockup-dot red" />
                <span className="mockup-dot yellow" />
                <span className="mockup-dot green" />
              </div>
              <div className="mockup-body">
                <div className="mockup-label">
                  {screenshotTabs[activeTab]} — Coming Soon
                </div>
                <div className="mockup-bars">
                  <div className="mockup-bar" style={{ width: "80%" }} />
                  <div className="mockup-bar" style={{ width: "60%" }} />
                  <div className="mockup-bar" style={{ width: "90%" }} />
                  <div className="mockup-bar" style={{ width: "45%" }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
