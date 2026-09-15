import express from "express";
import request from "supertest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockProjectService = vi.hoisted(() => ({
  create: vi.fn(),
  createWorkspace: vi.fn(),
  getById: vi.fn(),
  listWorkspaces: vi.fn(),
  resolveByReference: vi.fn(),
  update: vi.fn(),
  updateWorkspace: vi.fn(),
}));

const mockExecutionWorkspaceService = vi.hoisted(() => ({
  getById: vi.fn(),
  update: vi.fn(),
}));

const mockSecretService = vi.hoisted(() => ({
  normalizeEnvBindingsForPersistence: vi.fn(),
}));

const mockEnvironmentService = vi.hoisted(() => ({
  getById: vi.fn(),
}));

const mockWorkspaceOperationService = vi.hoisted(() => ({}));
const mockWorkspaceRuntimeLeaseService = vi.hoisted(() => ({
  claim: vi.fn(async () => ({ outcome: "created", ownerKey: "issue:issue-1", lease: null, reclaimedFrom: null })),
  release: vi.fn(async () => ({ released: false, ownerKey: null })),
  get: vi.fn(async () => null),
}));
const mockHeartbeatService = vi.hoisted(() => ({}));
const mockLogActivity = vi.hoisted(() => vi.fn());
const mockStartRuntimeServices = vi.hoisted(() => vi.fn());
const mockStopRuntimeServices = vi.hoisted(() => vi.fn());
const mockGetTelemetryClient = vi.hoisted(() => vi.fn());
const mockAccessService = vi.hoisted(() => ({
  decide: vi.fn(),
}));
const mockAssertCanManageProjectWorkspaceRuntimeServices = vi.hoisted(() => vi.fn());
const mockAssertCanManageExecutionWorkspaceRuntimeServices = vi.hoisted(() => vi.fn());

vi.mock("../telemetry.js", () => ({
  getTelemetryClient: mockGetTelemetryClient,
}));

vi.mock("../services/index.js", () => ({
  accessService: () => mockAccessService,
  environmentService: () => mockEnvironmentService,
  executionWorkspaceService: () => mockExecutionWorkspaceService,
  heartbeatService: () => mockHeartbeatService,
  logActivity: mockLogActivity,
  projectService: () => mockProjectService,
  secretService: () => mockSecretService,
  workspaceOperationService: () => mockWorkspaceOperationService,
  workspaceRuntimeLeaseService: () => mockWorkspaceRuntimeLeaseService,
  LEASED_WORKSPACE_RUNTIME_ACTIONS: ["start", "stop", "restart", "repair"],
}));

vi.mock("../services/workspace-runtime.js", () => ({
  cleanupExecutionWorkspaceArtifacts: vi.fn(),
  startRuntimeServicesForWorkspaceControl: mockStartRuntimeServices,
  stopRuntimeServicesForExecutionWorkspace: mockStopRuntimeServices,
  stopRuntimeServicesForProjectWorkspace: vi.fn(),
}));

vi.mock("../routes/workspace-runtime-service-authz.js", () => ({
  assertCanManageProjectWorkspaceRuntimeServices: mockAssertCanManageProjectWorkspaceRuntimeServices,
  assertCanManageExecutionWorkspaceRuntimeServices: mockAssertCanManageExecutionWorkspaceRuntimeServices,
}));

function registerWorkspaceRouteMocks() {
  vi.doMock("../telemetry.js", () => ({
    getTelemetryClient: mockGetTelemetryClient,
  }));

  vi.doMock("../services/index.js", () => ({
    accessService: () => mockAccessService,
    environmentService: () => mockEnvironmentService,
    executionWorkspaceService: () => mockExecutionWorkspaceService,
    heartbeatService: () => mockHeartbeatService,
    logActivity: mockLogActivity,
    projectService: () => mockProjectService,
    secretService: () => mockSecretService,
    workspaceOperationService: () => mockWorkspaceOperationService,
    workspaceRuntimeLeaseService: () => mockWorkspaceRuntimeLeaseService,
    LEASED_WORKSPACE_RUNTIME_ACTIONS: ["start", "stop", "restart", "repair"],
  }));

  vi.doMock("../services/workspace-runtime.js", () => ({
    cleanupExecutionWorkspaceArtifacts: vi.fn(),
    startRuntimeServicesForWorkspaceControl: mockStartRuntimeServices,
    stopRuntimeServicesForExecutionWorkspace: mockStopRuntimeServices,
    stopRuntimeServicesForProjectWorkspace: vi.fn(),
  }));

  vi.doMock("../routes/workspace-runtime-service-authz.js", () => ({
    assertCanManageProjectWorkspaceRuntimeServices: mockAssertCanManageProjectWorkspaceRuntimeServices,
    assertCanManageExecutionWorkspaceRuntimeServices: mockAssertCanManageExecutionWorkspaceRuntimeServices,
  }));
}

let appImportCounter = 0;

async function createProjectApp(actor: Record<string, unknown>) {
  registerWorkspaceRouteMocks();
  appImportCounter += 1;
  const routeModulePath = `../routes/projects.js?workspace-runtime-routes-authz-${appImportCounter}`;
  const middlewareModulePath = `../middleware/index.js?workspace-runtime-routes-authz-${appImportCounter}`;
  const [{ projectRoutes }, { errorHandler }] = await Promise.all([
    import(routeModulePath) as Promise<typeof import("../routes/projects.js")>,
    import(middlewareModulePath) as Promise<typeof import("../middleware/index.js")>,
  ]);
  const app = express();
  app.use(express.json());
  app.use((req, _res, next) => {
    (req as any).actor = actor;
    next();
  });
  app.use("/api", projectRoutes({} as any));
  app.use(errorHandler);
  return app;
}

async function createExecutionWorkspaceApp(actor: Record<string, unknown>) {
  registerWorkspaceRouteMocks();
  appImportCounter += 1;
  const routeModulePath = `../routes/execution-workspaces.js?workspace-runtime-routes-authz-${appImportCounter}`;
  const middlewareModulePath = `../middleware/index.js?workspace-runtime-routes-authz-${appImportCounter}`;
  const [{ executionWorkspaceRoutes }, { errorHandler }] = await Promise.all([
    import(routeModulePath) as Promise<typeof import("../routes/execution-workspaces.js")>,
    import(middlewareModulePath) as Promise<typeof import("../middleware/index.js")>,
  ]);
  const app = express();
  app.use(express.json());
  app.use((req, _res, next) => {
    (req as any).actor = actor;
    next();
  });
  app.use("/api", executionWorkspaceRoutes({} as any));
  app.use(errorHandler);
  return app;
}

function buildProject(overrides: Record<string, unknown> = {}) {
  return {
    id: "project-1",
    companyId: "company-1",
    urlKey: "project-1",
    goalId: null,
    goalIds: [],
    goals: [],
    name: "Project",
    description: null,
    status: "backlog",
    leadAgentId: null,
    targetDate: null,
    color: null,
    env: null,
    pauseReason: null,
    pausedAt: null,
    executionWorkspacePolicy: null,
    codebase: null,
    workspaces: [],
    primaryWorkspace: null,
    archivedAt: null,
    createdAt: new Date(),
    updatedAt: new Date(),
    ...overrides,
  };
}

function buildExecutionWorkspace(overrides: Record<string, unknown> = {}) {
  return {
    id: "workspace-1",
    companyId: "company-1",
    projectId: "project-1",
    projectWorkspaceId: null,
    sourceIssueId: null,
    mode: "isolated_workspace",
    strategyType: "git_worktree",
    name: "Workspace",
    status: "active",
    cwd: "/tmp/workspace",
    repoUrl: null,
    baseRef: "main",
    branchName: "feature/test",
    providerType: "git_worktree",
    providerRef: null,
    derivedFromExecutionWorkspaceId: null,
    lastUsedAt: new Date(),
    openedAt: new Date(),
    closedAt: null,
    cleanupEligibleAt: null,
    cleanupReason: null,
    config: null,
    metadata: null,
    runtimeServices: [],
    createdAt: new Date(),
    updatedAt: new Date(),
    ...overrides,
  };
}

describe.sequential("workspace runtime service route authorization", () => {
  const projectId = "11111111-1111-4111-8111-111111111111";
  const workspaceId = "22222222-2222-4222-8222-222222222222";
  const executionWorkspaceId = "33333333-3333-4333-8333-333333333333";

  beforeEach(() => {
    vi.clearAllMocks();
    mockAccessService.decide.mockResolvedValue({
      allowed: true,
      action: "company_scope:read",
      reason: "allow_test",
      explanation: "Allowed by test mock.",
    });
    mockEnvironmentService.getById.mockResolvedValue(null);
    mockSecretService.normalizeEnvBindingsForPersistence.mockImplementation(async (_companyId, env) => env);
    mockProjectService.resolveByReference.mockResolvedValue({ ambiguous: false, project: null });
    mockProjectService.create.mockResolvedValue(buildProject());
    mockProjectService.update.mockResolvedValue(buildProject());
    mockProjectService.createWorkspace.mockResolvedValue({
      id: workspaceId,
      companyId: "company-1",
      projectId,
      name: "Workspace",
      sourceType: "local_path",
      cwd: "/tmp/project",
      repoUrl: null,
      repoRef: null,
      defaultRef: null,
      visibility: "default",
      setupCommand: null,
      cleanupCommand: null,
      remoteProvider: null,
      remoteWorkspaceRef: null,
      sharedWorkspaceKey: null,
      metadata: null,
      runtimeConfig: null,
      isPrimary: false,
      runtimeServices: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    });
    mockProjectService.listWorkspaces.mockResolvedValue([{
      id: workspaceId,
      companyId: "company-1",
      projectId,
      name: "Workspace",
      sourceType: "local_path",
      cwd: "/tmp/project",
      repoUrl: null,
      repoRef: null,
      defaultRef: null,
      visibility: "default",
      setupCommand: null,
      cleanupCommand: null,
      remoteProvider: null,
      remoteWorkspaceRef: null,
      sharedWorkspaceKey: null,
      metadata: null,
      runtimeConfig: null,
      isPrimary: false,
      runtimeServices: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    }]);
    mockProjectService.updateWorkspace.mockResolvedValue({
      id: workspaceId,
      companyId: "company-1",
      projectId,
      name: "Workspace",
      sourceType: "local_path",
      cwd: "/tmp/project",
      repoUrl: null,
      repoRef: null,
      defaultRef: null,
      visibility: "default",
      setupCommand: null,
      cleanupCommand: null,
      remoteProvider: null,
      remoteWorkspaceRef: null,
      sharedWorkspaceKey: null,
      metadata: null,
      runtimeConfig: null,
      isPrimary: false,
      runtimeServices: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    });
    mockExecutionWorkspaceService.update.mockResolvedValue(buildExecutionWorkspace());
    mockAssertCanManageProjectWorkspaceRuntimeServices.mockResolvedValue(undefined);
    mockAssertCanManageExecutionWorkspaceRuntimeServices.mockResolvedValue(undefined);
  });

  it("rejects agent callers for project workspace runtime service mutations when workspace auth denies access", async () => {
    const { forbidden } = await import("../errors.js");
    mockProjectService.getById.mockResolvedValue(buildProject({
      id: projectId,
      workspaces: [{
        id: workspaceId,
        companyId: "company-1",
        projectId,
        name: "Workspace",
        sourceType: "local_path",
        cwd: "/tmp/project",
        repoUrl: null,
        repoRef: null,
        defaultRef: null,
        visibility: "default",
        setupCommand: null,
        cleanupCommand: null,
        remoteProvider: null,
        remoteWorkspaceRef: null,
        sharedWorkspaceKey: null,
        metadata: null,
        runtimeConfig: null,
        isPrimary: false,
        runtimeServices: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      }],
    }));
    mockAssertCanManageProjectWorkspaceRuntimeServices.mockRejectedValue(
      forbidden("Missing permission to manage workspace runtime services"),
    );
    const app = await createProjectApp({
      type: "agent",
      agentId: "agent-1",
      companyId: "company-1",
      source: "agent_key",
      runId: "run-1",
    });

    const res = await request(app)
      .post(`/api/projects/${projectId}/workspaces/${workspaceId}/runtime-services/start`)
      .send({});

    expect(res.status).toBe(403);
    expect(res.body.error).toContain("Missing permission");
    expect(mockProjectService.getById).toHaveBeenCalledWith(projectId);
    expect(mockAssertCanManageProjectWorkspaceRuntimeServices).toHaveBeenCalled();
  }, 15000);

  it("blocks shared-project stop/restart requests from agents", async () => {
    mockProjectService.getById.mockResolvedValue(buildProject({
      id: projectId,
      workspaces: [{
        id: workspaceId,
        companyId: "company-1",
        projectId,
        name: "Workspace",
        sourceType: "local_path",
        cwd: "/tmp/project",
        repoUrl: null,
        repoRef: null,
        defaultRef: null,
        visibility: "default",
        setupCommand: null,
        cleanupCommand: null,
        remoteProvider: null,
        remoteWorkspaceRef: null,
        sharedWorkspaceKey: "shared-key",
        metadata: null,
        runtimeConfig: null,
        isPrimary: false,
        runtimeServices: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      }],
    }));
    const app = await createProjectApp({
      type: "agent",
      agentId: "agent-1",
      companyId: "company-1",
      source: "agent_key",
      runId: "run-1",
    });

    const responses = await Promise.all([
      request(app).post(`/api/projects/${projectId}/workspaces/${workspaceId}/runtime-services/stop`).send({}),
      request(app).post(`/api/projects/${projectId}/workspaces/${workspaceId}/runtime-services/restart`).send({}),
    ]);

    for (const res of responses) {
      expect(res.status).toBe(403);
      expect(res.body.error).toContain("Missing permission");
      expect(mockProjectService.getById).toHaveBeenCalledWith(projectId);
      expect(mockAssertCanManageProjectWorkspaceRuntimeServices).not.toHaveBeenCalled();
    }

  }, 15000);

  it("rejects agent callers that create project execution workspace commands", async () => {
    const app = await createProjectApp({
      type: "agent",
      agentId: "agent-1",
      companyId: "company-1",
      source: "agent_key",
      runId: "run-1",
    });

    const res = await request(app)
      .post("/api/companies/company-1/projects")
      .send({
        name: "Exploit",
        executionWorkspacePolicy: {
          enabled: true,
          workspaceStrategy: {
            type: "git_worktree",
            provisionCommand: "touch /tmp/paperclip-rce",
            runtimeProvisionCommand: "touch /tmp/paperclip-runtime-rce",
          },
        },
      });

    expect(res.status).toBe(403);
    expect(res.body.error).toContain("host-executed workspace commands");
    expect(mockProjectService.create).not.toHaveBeenCalled();
  });

  it("rejects agent callers that update project workspace cleanup commands", async () => {
    mockProjectService.getById.mockResolvedValue(buildProject());
    const app = await createProjectApp({
      type: "agent",
      agentId: "agent-1",
      companyId: "company-1",
      source: "agent_key",
      runId: "run-1",
    });

    const res = await request(app)
      .patch(`/api/projects/${projectId}/workspaces/${workspaceId}`)
      .send({
        cleanupCommand: "rm -rf /tmp/paperclip-rce",
      });

    expect(res.status).toBe(403);
    expect(res.body.error).toContain("host-executed workspace commands");
    expect(mockProjectService.updateWorkspace).not.toHaveBeenCalled();
  });

  it("allows board callers through the project workspace runtime auth gate", async () => {
    mockProjectService.getById.mockResolvedValue(null);
    const app = await createProjectApp({
      type: "board",
      userId: "board-1",
      companyIds: ["company-1"],
      source: "session",
      isInstanceAdmin: false,
    });

    const res = await request(app)
      .post(`/api/projects/${projectId}/workspaces/${workspaceId}/runtime-services/start`)
      .send({});

    expect(res.status).toBe(404);
    expect(res.body.error).toContain("Project not found");
    expect(mockProjectService.getById).toHaveBeenCalledWith(projectId);
  });

  it("rejects agent callers for execution workspace runtime service mutations when workspace auth denies access", async () => {
    const { forbidden } = await import("../errors.js");
    mockExecutionWorkspaceService.getById.mockResolvedValue(buildExecutionWorkspace({ id: executionWorkspaceId }));
    mockAssertCanManageExecutionWorkspaceRuntimeServices.mockRejectedValue(
      forbidden("Missing permission to manage workspace runtime services"),
    );
    const app = await createExecutionWorkspaceApp({
      type: "agent",
      agentId: "agent-1",
      companyId: "company-1",
      source: "agent_key",
      runId: "run-1",
    });

    const res = await request(app)
      .post(`/api/execution-workspaces/${executionWorkspaceId}/runtime-services/restart`)
      .send({});

    expect(res.status).toBe(403);
    expect(res.body.error).toContain("Missing permission");
    expect(mockExecutionWorkspaceService.getById).toHaveBeenCalledWith(executionWorkspaceId);
    expect(mockAssertCanManageExecutionWorkspaceRuntimeServices).toHaveBeenCalled();
  }, 15000);

  it("attaches an eligible loopback runtime without restarting, recreating, or changing its identity", async () => {
    const runtimeService = {
      id: "44444444-4444-4444-8444-444444444444",
      companyId: "company-1",
      projectId: "project-1",
      projectWorkspaceId: null,
      executionWorkspaceId,
      issueId: "55555555-5555-4555-8555-555555555555",
      scopeType: "run",
      scopeId: "66666666-6666-4666-8666-666666666666",
      serviceName: "academy-browser",
      status: "running",
      lifecycle: "shared",
      reuseKey: "reuse-key",
      command: "python -m flask run",
      cwd: "/tmp/workspace",
      port: 37111,
      url: "http://127.0.0.1:37111",
      provider: "local_process",
      providerRef: "pid-123",
      ownerAgentId: "agent-1",
      startedByRunId: "run-1",
      lastUsedAt: new Date(),
      startedAt: new Date("2026-09-15T20:35:54.070Z"),
      stoppedAt: null,
      healthStatus: "healthy",
      exposure: null,
      configIndex: null,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    const workspace = buildExecutionWorkspace({ id: executionWorkspaceId, runtimeServices: [runtimeService] });
    mockExecutionWorkspaceService.getById.mockResolvedValue(workspace);
    const app = await createExecutionWorkspaceApp({
      type: "agent",
      agentId: "agent-1",
      companyId: "company-1",
      source: "agent_key",
      runId: "run-1",
    });

    const res = await request(app)
      .post(`/api/execution-workspaces/${executionWorkspaceId}/runtime-services/attach`)
      .send({ runtimeServiceId: runtimeService.id });

    expect(res.status).toBe(200);
    expect(res.body.attachment).toEqual({
      runtimeServiceId: runtimeService.id,
      purpose: "non_production_evidence",
      url: runtimeService.url,
      loopbackOnly: true,
      exposure: null,
    });
    expect(mockExecutionWorkspaceService.update).not.toHaveBeenCalled();
    expect(mockStartRuntimeServices).not.toHaveBeenCalled();
    expect(mockStopRuntimeServices).not.toHaveBeenCalled();
    expect(mockLogActivity).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({
      action: "execution_workspace.runtime_attached",
      runId: "run-1",
      details: expect.objectContaining({
        outcome: "attached",
        timestamp: expect.any(String),
        runtimeService: expect.objectContaining({
          id: runtimeService.id,
          serviceName: "academy-browser",
          sourceRef: "main",
          scopeType: "run",
          scopeId: runtimeService.scopeId,
          lifecycle: "shared",
          port: 37111,
          url: "http://127.0.0.1:37111",
          providerRef: "pid-123",
          exposure: null,
        }),
      }),
    }));
  });

  it("fails closed when an attachment target is exposed or authorization is denied", async () => {
    const exposedService = {
      ...buildExecutionWorkspace().runtimeServices[0],
      id: "44444444-4444-4444-8444-444444444444",
      companyId: "company-1",
      executionWorkspaceId,
      scopeType: "run",
      scopeId: "66666666-6666-4666-8666-666666666666",
      serviceName: "academy-browser",
      status: "running",
      lifecycle: "shared",
      port: 37111,
      url: "http://127.0.0.1:37111",
      exposure: { type: "tailscale_https" },
    };
    mockExecutionWorkspaceService.getById.mockResolvedValue(
      buildExecutionWorkspace({ id: executionWorkspaceId, runtimeServices: [exposedService] }),
    );
    const app = await createExecutionWorkspaceApp({
      type: "agent",
      agentId: "agent-1",
      companyId: "company-1",
      source: "agent_key",
      runId: "run-1",
    });

    const ineligible = await request(app)
      .post(`/api/execution-workspaces/${executionWorkspaceId}/runtime-services/attach`)
      .send({ runtimeServiceId: exposedService.id });
    expect(ineligible.status).toBe(422);
    expect(ineligible.body.error).toContain("not eligible");
    expect(mockLogActivity).not.toHaveBeenCalled();

    const { forbidden } = await import("../errors.js");
    mockAssertCanManageExecutionWorkspaceRuntimeServices.mockRejectedValueOnce(
      forbidden("Missing permission to manage workspace runtime services"),
    );
    const denied = await request(app)
      .post(`/api/execution-workspaces/${executionWorkspaceId}/runtime-services/attach`)
      .send({ runtimeServiceId: exposedService.id });
    expect(denied.status).toBe(403);
    expect(denied.body.error).toContain("Missing permission");
    expect(mockLogActivity).not.toHaveBeenCalled();
  });

  it("rejects agent callers that patch execution workspace command config", async () => {
    mockExecutionWorkspaceService.getById.mockResolvedValue(buildExecutionWorkspace({ id: executionWorkspaceId }));
    const app = await createExecutionWorkspaceApp({
      type: "agent",
      agentId: "agent-1",
      companyId: "company-1",
      source: "agent_key",
      runId: "run-1",
    });

    const res = await request(app)
      .patch(`/api/execution-workspaces/${executionWorkspaceId}`)
      .send({
        config: {
          cleanupCommand: "rm -rf /tmp/paperclip-rce",
        },
      });

    expect(res.status).toBe(403);
    expect(res.body.error).toContain("host-executed workspace commands");
    expect(mockExecutionWorkspaceService.update).not.toHaveBeenCalled();
  });

  it("rejects agent callers that smuggle execution workspace commands through metadata.config", async () => {
    mockExecutionWorkspaceService.getById.mockResolvedValue(buildExecutionWorkspace({ id: executionWorkspaceId }));
    const app = await createExecutionWorkspaceApp({
      type: "agent",
      agentId: "agent-1",
      companyId: "company-1",
      source: "agent_key",
      runId: "run-1",
    });

    const res = await request(app)
      .patch(`/api/execution-workspaces/${executionWorkspaceId}`)
      .send({
        metadata: {
          config: {
            provisionCommand: "touch /tmp/paperclip-rce",
          },
        },
      });

    expect(res.status).toBe(403);
    expect(res.body.error).toContain("host-executed workspace commands");
    expect(mockExecutionWorkspaceService.update).not.toHaveBeenCalled();
  });

  it("allows board callers through the execution workspace runtime auth gate", async () => {
    mockExecutionWorkspaceService.getById.mockResolvedValue(null);
    const app = await createExecutionWorkspaceApp({
      type: "board",
      userId: "board-1",
      companyIds: ["company-1"],
      source: "session",
      isInstanceAdmin: false,
    });

    const res = await request(app)
      .post(`/api/execution-workspaces/${executionWorkspaceId}/runtime-services/restart`)
      .send({});

    expect(res.status).toBe(404);
    expect(res.body.error).toContain("Execution workspace not found");
    expect(mockExecutionWorkspaceService.getById).toHaveBeenCalledWith(executionWorkspaceId);
  });
});
