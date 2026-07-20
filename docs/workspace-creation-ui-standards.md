# Workspace Creation UI Standards

The operational workspace wizard at `/app/workspaces/new` uses the `cw-workspace-creation` component system. It is scoped to the workspace route so organization and entity onboarding flows retain their own layout contracts.

The entity and equity routes use the parallel `cw-entity-creation` and `cw-equity-creation` namespaces with the shared `cw-specialized-*` primitives. These apply the same control height, square border, progress rail, and responsive form rules while also standardizing legal-entity tiles, equity-type cards, and shareholder rows.

## Reusable Primitives

| Class | Purpose |
| --- | --- |
| `cw-workspace-card` | Bounded form surface with squared border and compact padding. |
| `cw-workspace-progress` | Four-step horizontal progress rail with stable labels and connected states. |
| `cw-input`, `cw-select` | 46px controls with identical padding, border, hover, focus, and disabled states. |
| `cw-btn--primary`, `cw-btn--ghost` | Compact primary and secondary actions with consistent height and spacing. |
| `cw-module-card` | Selectable module tile with a blue active rail and no layout shift. |

## Visual Contract

- Use the scoped navy header (`#102a43`), blue action and focus color (`#1769e0`), charcoal text, and light neutral backgrounds.
- Use 2px corners, visible borders, and restrained shadows. Avoid oversized controls, gradients, or decorative shapes.
- Labels are 12px semibold; controls are 14px; step titles are 22px bold. Keep all text within its surface.
- Use two columns on desktop for form fields, a bounded 940px form width, and one column on narrow screens.

## Interaction Contract

- Continue buttons remain disabled until the current step is valid.
- Dropdowns use the same 46px control contract as text inputs and expose hover, focus, and disabled states.
- The progress rail remains horizontally scrollable on narrow viewports instead of compressing step labels.
- Module selections use the existing workspace template payload and do not change provisioning behavior.

## Governed Departments

- `EnterpriseDepartmentSelector` exposes only the approved department catalog; creation flows submit department keys, never ad-hoc department names.
- The shared entity creation workflow validates the keys, provisions `EntityDepartment` records, mirrors them into the linked workspace as `WorkspaceGroup` records, and logs `department.provisioned` to the platform audit stream.
- Existing entity department controls remain the post-creation management surface. Workspace owners and admins manage linked department groups through the workspace department controls; organization access remains enforced by entity scope and role controls.
- Department records are included in the existing governance YAML export and recovery import payloads.