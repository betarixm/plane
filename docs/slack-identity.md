# External identity source (Slack adapter)

This Plane deployment uses one Slack workspace as the only source of human
identity and workspace membership. Plane mirrors Slack-owned identity fields
into local `User` and `WorkspaceMember` rows for sessions and relational data;
`Profile` contains only Plane-specific preferences.

## Provider boundary

Slack is the only installed adapter, not a core identity type. The core schema
stores a provider-neutral `IdentitySource` and `ExternalIdentity`, sessions are
bound to a source ID and generation, and the public instance configuration
exposes one generic `identity_source` object. Provider tokens, OAuth/OIDC,
events, profile mapping, and role mapping stay inside the provider adapter.

`discord` is already a recognized provider key and frontend descriptor, but it
is intentionally reported as unconfigured because this build has no Discord
adapter. Adding Discord requires registering its backend adapter and routes,
implementing install/login plus server-member reconciliation, and enabling its
deployment credentials. It does not require another user model, workspace
model, session contract, or instance API shape.

## Slack app configuration

Set these values in `apps/api/.env` before opening Plane for the first time:

```env
IDENTITY_PROVIDER="slack"
SLACK_CLIENT_ID=""
SLACK_CLIENT_SECRET=""
SLACK_SIGNING_SECRET=""
```

Restart the API after changing these values. The process environment is the
only configuration source; Plane does not persist deployment secrets in its
database or provide an API for changing them at runtime.

Configure the Slack app with the public Plane API origin:

- OAuth redirect: `<origin>/auth/slack/install/callback/`
- Sign in with Slack redirect: `<origin>/auth/slack/callback/`
- Events request URL: `<origin>/auth/slack/events/`

The installation flow requests these bot scopes:

- `team:read`
- `users:read`
- `users:read.email`

Enable the `team_join`, `user_change`, `team_rename`, `team_domain_change`,
`app_uninstalled`, and `tokens_revoked` events. Slack OpenID Connect sign-in
uses the separate `openid profile email` scope set; Slack does not allow those
scopes to be combined with bot installation scopes.

Leave Slack token rotation disabled for this lightweight deployment; the
current installation stores a long-lived encrypted bot token and treats an
explicit token revocation as a disconnected identity source.

## Bootstrap and sign-in

The initial Plane screen links directly to `/auth/slack/install/`; there is no
separate privileged administration application or instance-admin identity. The
person installing the app must be an active Slack workspace administrator or
owner. The callback binds that Slack team to the singleton Plane workspace and
creates the first mirrored administrator.

After setup, all users sign in through `/auth/slack/`. Plane pins the OpenID
request to the installed Slack team, validates the callback, fetches the
authoritative member record with the bot token, and refreshes the local
projection before creating a Plane session.

Slack owners and administrators map to Plane administrators, regular members
map to members, and restricted users map to guests. Slack bots, Slackbot,
Slack Connect external users, invited users, profile-only users, forgotten
users, and suspended users are not active Plane identities. Disabled, removed,
or otherwise ineligible Slack users are deactivated locally and their Plane
sessions are revoked. Every browser session is bound to the exact Slack
installation generation that created it, so reconnecting the Slack app also
invalidates sessions from the previous connection. Existing API keys are
accepted only while their owner has a live, generation-matched Slack
projection.

Events provide near-real-time updates. Verified event payloads are first stored
in a durable outbox, then dispatched with a bounded, no-retry broker publish;
a one-minute sweeper requeues broker or worker failures without asking Slack to
redeliver the event.
A persisted six-attempt budget prevents malformed or permanently unprocessable
events from looping forever; exhausted events remain as `dead_letter` receipts
for diagnosis until the 30-day receipt cleanup.
A full `users.list` reconciliation runs every 15 minutes to repair missed or
out-of-order events. Transient full-reconciliation failures are retried without
immediately suspending users. Terminal bot authentication failures, or an
exhausted full-reconciliation retry chain, revoke the installation and fail
closed.

Member removals that arrive before Plane has ever seen that person are kept as
negative Slack tombstones, so an older in-flight roster snapshot cannot create
an active local identity afterward. Workspace rename/domain events trigger a
fresh `team.info` read; request-start watermarks keep slower old snapshots from
overwriting newer Slack metadata.

Signed events received while bootstrap or reconnect is still committing are
also persisted. Installation generations, Slack event timestamps, and
authoritative request-start watermarks decide whether the event belongs to the
new connection. The callback performs its final `team.info`, `users.info`, and
`auth.test` validation while holding the singleton installation fence, so a
concurrent uninstall, token revocation, or member removal cannot be overwritten
by an older callback snapshot. If a current lifecycle event cannot be verified
after retries, Plane fails closed and revokes the installation before moving
the receipt to the dead-letter state.

If Slack uninstalls the app or revokes its bot token, Plane immediately
deactivates mirrored human identities and revokes their sessions. A Slack
administrator can restore the instance through `/auth/slack/install/`; the
reinstall is accepted only for the Slack team already bound to the singleton
workspace, then a full reconciliation is queued.

Slack access changes also invalidate collaborative page editing. Plane
publishes a post-commit revocation command to every Live server, which closes
the affected user's open WebSocket connections. Each connection additionally
revalidates page edit access against the primary API database at most every ten
seconds even when the client is completely passive, so a missed broker
notification cannot leave an indefinitely cached read authorization. The Live
authorization request has its own five-second timeout; an unavailable API is
therefore denied and the socket is closed instead of inheriting the general
twenty-second API timeout.

Identity ownership is shown in the regular workspace member and general settings.
If the identity source is revoked, the normal sign-in screen offers the fenced
Slack reinstall flow. Slack application credentials are supplied by the server
environment; Plane does not expose a separate privileged configuration UI.

Workspace and project email invitations are removed. Visible projects may be
joined only by an active Slack-projected member, and Slack guest/admin role
boundaries are enforced while holding the same installation lock used by the
sync worker. User-valued mutations such as assignees, subscribers, module
members/leads, and cycle owners accept only active project members whose Slack
projection belongs to the current installation generation; historical links
remain readable but cannot be used to restore a removed Slack member's access.
