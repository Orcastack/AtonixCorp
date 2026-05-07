// vars/gerrit.groovy
// Shared step: post build status and comments back to Gerrit.
// Used by all Ledgora pipelines.

def vote(Map args) {
    // args: verified (+1/-1/0), message
    def verified = args.verified ?: '0'
    def message  = args.message  ?: ''

    withCredentials([usernamePassword(
        credentialsId: 'gerrit-http-creds',
        usernameVariable: 'GERRIT_USER',
        passwordVariable: 'GERRIT_PASS'
    )]) {
        sh """
            set -e
            curl -sf \
              --user "\${GERRIT_USER}:\${GERRIT_PASS}" \
              -X POST \
              -H 'Content-Type: application/json' \
              -d '{
                "labels": {"Verified": ${verified}},
                "message": ${groovy.json.JsonOutput.toJson(message)}
              }' \
              "https://gerrit.ledgora.internal/a/changes/${env.GERRIT_CHANGE_ID}/revisions/${env.GERRIT_PATCHSET_REV ?: 'current'}/review"
        """
    }
}

def comment(Map args) {
    // args: changeId, message
    def changeId = args.changeId ?: env.GERRIT_CHANGE_ID
    def message  = args.message  ?: ''

    withCredentials([usernamePassword(
        credentialsId: 'gerrit-http-creds',
        usernameVariable: 'GERRIT_USER',
        passwordVariable: 'GERRIT_PASS'
    )]) {
        sh """
            set -e
            curl -sf \
              --user "\${GERRIT_USER}:\${GERRIT_PASS}" \
              -X POST \
              -H 'Content-Type: application/json' \
              -d '{"message": ${groovy.json.JsonOutput.toJson(message)}}' \
              "https://gerrit.ledgora.internal/a/changes/${changeId}/revisions/current/review"
        """
    }
}
