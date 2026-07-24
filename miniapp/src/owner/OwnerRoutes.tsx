import { Navigate, Route, Routes } from "react-router-dom";
import { appPaths } from "../routing/paths";
import { OwnerAudit } from "./OwnerAudit";
import { OwnerGroups } from "./OwnerGroups";
import { OwnerOverview } from "./OwnerOverview";
import { OwnerPayments } from "./OwnerPayments";
import { OwnerUsers } from "./OwnerUsers";
import type { OwnerWorkspace } from "./hooks/useOwnerWorkspace";

export function OwnerRoutes({ workspace }: { workspace: OwnerWorkspace }) {
  const { session } = workspace;
  if (!session) return null;
  return <Routes>
    <Route index element={session.actor.is_owner && workspace.overview ? <OwnerOverview data={workspace.overview} /> : <Navigate to="users" replace />} />
    <Route path="users/*" element={<OwnerUsers users={workspace.users} total={workspace.usersTotal} loading={workspace.busy} filters={workspace.userFilters} permissions={session.actor.permissions} onFiltersChange={workspace.setUserFilters} onRefresh={workspace.refreshUsersAfterMutation} />} />
    <Route path="groups" element={session.actor.is_owner ? <OwnerGroups groups={workspace.groups} total={workspace.groupsTotal} loading={workspace.busy} query={workspace.groupQuery} onQueryChange={workspace.setGroupQuery} onRefresh={() => void workspace.loadGroups()} onUpdate={workspace.updateGroup} /> : <Navigate to={appPaths.owner.users} replace />} />
    <Route path="payments" element={session.actor.is_owner ? <OwnerPayments /> : <Navigate to={appPaths.owner.users} replace />} />
    <Route path="audit" element={session.actor.is_owner ? <OwnerAudit items={workspace.audit} loading={workspace.busy} onRefresh={() => void workspace.loadAudit()} /> : <Navigate to={appPaths.owner.users} replace />} />
    <Route path="*" element={<Navigate to={appPaths.owner.users} replace />} />
  </Routes>;
}
