// vars/openstack.groovy
// Shared OpenStack utility steps for Ledgora pipelines.

/**
 * Run a terraform command in the given environment root directory,
 * injecting OpenStack application credentials from Jenkins credentials store.
 *
 * Usage:
 *   openstack.terraform(env: 'dev', command: 'plan -out=plan.tfplan')
 */
def terraform(Map args) {
    def envName  = args.env     ?: error('openstack.terraform: env is required')
    def command  = args.command ?: error('openstack.terraform: command is required')
    def changeId = args.changeId ?: env.GERRIT_CHANGE_ID ?: 'unknown'
    def commit   = args.commit   ?: (env.GERRIT_PATCHSET_REVISION?.take(8) ?: 'unknown')

    dir("infra/openstack/terraform/envs/${envName}") {
        withCredentials([
            string(credentialsId: "openstack-${envName}-appid",     variable: 'OS_APPLICATION_CREDENTIAL_ID'),
            string(credentialsId: "openstack-${envName}-appsecret", variable: 'OS_APPLICATION_CREDENTIAL_SECRET'),
            string(credentialsId: "lgx-${envName}-ssh-pubkey",      variable: 'TF_VAR_ssh_public_key')
        ]) {
            sh """
                set -e
                terraform ${command} \
                  -var="change_id=${changeId}" \
                  -var="commit=${commit}" \
                  -var="os_application_credential_id=\${OS_APPLICATION_CREDENTIAL_ID}" \
                  -var="os_application_credential_secret=\${OS_APPLICATION_CREDENTIAL_SECRET}"
            """
        }
    }
}

/**
 * Extract the plan summary line from a terraform plan output file.
 * Returns a single-line summary string.
 */
def planSummary(String planFile) {
    def text = readFile(planFile)
    return text.readLines()
               .findAll { it =~ /Plan:|No changes|Error/ }
               .join(' | ')
               .trim()
}
