#!/usr/bin/env sh

set -eu

mode="${1:?usage: run_terraform_pipeline.sh <plan|apply> <environment>}"
environment_name="${2:?usage: run_terraform_pipeline.sh <plan|apply> <environment>}"
upper_environment="$(printf '%s' "$environment_name" | tr '[:lower:]' '[:upper:]')"
environment_dir="infra/terraform/environments/$environment_name"
role_arn_var="${upper_environment}_TERRAFORM_ROLE_ARN"

read_env() {
  variable_name="$1"
  eval "printf '%s' \"\${$variable_name-}\""
}

role_arn="$(read_env "$role_arn_var")"
if [ -z "$role_arn" ]; then
  echo "Missing required environment variable: $role_arn_var" >&2
  exit 1
fi

export TF_IN_AUTOMATION=true
export TF_INPUT=0

. tools/ci/bootstrap_bitbucket_oidc.sh "$role_arn"
. tools/ci/render_terraform_auto_tfvars.sh "$environment_name"

cd "$environment_dir"

terraform init \
  -backend-config="bucket=$TF_STATE_BUCKET" \
  -backend-config="key=ledgora/$environment_name/terraform.tfstate" \
  -backend-config="region=$AWS_DEFAULT_REGION" \
  -backend-config="dynamodb_table=$TF_STATE_LOCK_TABLE" \
  -backend-config="encrypt=true"

terraform fmt -check -recursive ../..
terraform validate

if [ "$mode" = "plan" ]; then
  terraform plan -input=false -out=tfplan
elif [ "$mode" = "apply" ]; then
  terraform apply -input=false -auto-approve
else
  echo "Unsupported mode: $mode" >&2
  exit 1
fi
