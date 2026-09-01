CREATE TABLE IF NOT EXISTS tweco_model_revisions (
    model_id VARCHAR(36) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    revision INTEGER NOT NULL,
    contract_version VARCHAR(16) NOT NULL,
    payload TEXT NOT NULL,
    created_at VARCHAR(64) NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    reason TEXT NOT NULL,
    PRIMARY KEY (model_id, revision)
);
CREATE INDEX IF NOT EXISTS ix_tweco_model_project ON tweco_model_revisions (project_id, model_id, revision);
CREATE TABLE IF NOT EXISTS tweco_calculation_snapshots (
    snapshot_id VARCHAR(64) PRIMARY KEY,
    model_id VARCHAR(36) NOT NULL,
    revision INTEGER NOT NULL,
    scenario_id VARCHAR(255) NOT NULL,
    payload TEXT NOT NULL,
    created_at VARCHAR(64) NOT NULL,
    FOREIGN KEY (model_id, revision) REFERENCES tweco_model_revisions(model_id, revision)
);
