import { roadmapMilestones } from "../data";

const statusColors: Record<string, string> = {
  completed: "#22c55e",
  "in-progress": "#6c63ff",
  upcoming: "#7a7f99",
};

const statusLabels: Record<string, string> = {
  completed: "Completed",
  "in-progress": "In Progress",
  upcoming: "Upcoming",
};

export default function Roadmap() {
  return (
    <section className="roadmap-section">
      <div className="section-container">
        <div className="section-badge">Roadmap</div>
        <h2 className="section-title">Coming soon: The roadmap</h2>
        <p className="section-subtitle">
          A transparent view of what's being built and what's coming next.
        </p>
        <div className="roadmap-timeline">
          {roadmapMilestones.map((milestone, i) => (
            <div key={milestone.version} className="roadmap-item">
              <div className="roadmap-marker">
                <div
                  className="roadmap-dot"
                  style={{ background: statusColors[milestone.status] }}
                />
                {i < roadmapMilestones.length - 1 && (
                  <div className="roadmap-line" />
                )}
              </div>
              <div className="roadmap-content">
                <div className="roadmap-header">
                  <span className="roadmap-version">{milestone.version}</span>
                  <span
                    className="roadmap-status"
                    style={{
                      color: statusColors[milestone.status],
                      borderColor: statusColors[milestone.status],
                    }}
                  >
                    {statusLabels[milestone.status]}
                  </span>
                </div>
                <h3 className="roadmap-title">{milestone.title}</h3>
                <p className="roadmap-desc">{milestone.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
