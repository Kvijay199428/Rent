import { roadmapMilestones } from "../data";

const statusLabels: Record<string, string> = {
  completed: "Completed",
  "in-progress": "In Progress",
  upcoming: "Upcoming",
};

export default function Roadmap() {
  return (
    <section className="roadmap-section">
      <div className="section-container">
        <div className="section-header">
          <span className="section-badge">04 — Roadmap</span>
          <h2 className="section-title">The Roadmap</h2>
          <div className="section-rule" />
          <p className="section-subtitle">
            A transparent view of what's being built and what's coming next.
          </p>
        </div>
        <div className="roadmap-timeline">
          {roadmapMilestones.map((milestone) => (
            <div key={milestone.version} className="roadmap-item">
              <div className="roadmap-dot" />
              <div className="roadmap-marker">{milestone.version}</div>
              <span className="roadmap-status">{statusLabels[milestone.status]}</span>
              <h3 className="roadmap-title">{milestone.title}</h3>
              <p className="roadmap-desc">{milestone.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
