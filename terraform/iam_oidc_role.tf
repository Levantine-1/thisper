# GitHub Actions assumes this role via OIDC (short-lived federated tokens)
# instead of a long-lived static IAM user key. The OIDC provider itself is
# account-wide and created once in the core terraform repo
# (iam/oidc/github_oidc_provider.tf) -- referenced here by its known ARN
# directly (not a data source: reading it back via IAM would need an
# iam:GetOpenIDConnectProvider grant this role has no other use for, just
# to echo back the same ARN we already have). Never created per-repo (a
# second provider for the same issuer URL would collide).
locals {
  github_oidc_provider_arn = "arn:aws:iam::975050308029:oidc-provider/token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.github_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Scoped to pushes to master specifically (this repo's actual default
    # branch), not a bare repo:* wildcard.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:Levantine-1/thisper:ref:refs/heads/master"]
    }
  }
}

resource "aws_iam_role" "github_actions_thisper" {
  name               = "github_actions_thisper"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json
}

# ecr/ec2/route53 statements mirror the core repo's terraform/iam/policies/
# terraform_thisper_policy.tf (granted to the old static-key IAM user) --
# kept self-contained here rather than referencing that module, since the
# point of this migration is per-repo terraform ownership. The s3
# statements are new: that old policy never needed bucket access because
# Jenkins ran this repo's terraform against local state, not the shared
# S3 backend this migration moves it onto.
resource "aws_iam_role_policy" "github_actions_thisper_policy" {
  name = "github_actions_thisper_policy"
  role = aws_iam_role.github_actions_thisper.id

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:GetRole",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:GetRolePolicy",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy"
            ],
            "Resource": "arn:aws:iam::975050308029:role/github_actions_thisper"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:CreateRepository",
                "ecr:DeleteRepository",
                "ecr:DescribeRepositories",
                "ecr:PutImage",
                "ecr:BatchDeleteImage",
                "ecr:BatchGetImage",
                "ecr:DescribeImages",
                "ecr:GetDownloadUrlForLayer",
                "ecr:ListTagsForResource",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:BatchCheckLayerAvailability"
            ],
            "Resource": "arn:aws:ecr:${var.region}:975050308029:repository/thisper"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceTypes",
                "ec2:DescribeVolumes",
                "ec2:DescribeInstanceAttribute",
                "ec2:DescribeInstanceCreditSpecifications"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "route53:ListHostedZones",
                "route53:GetHostedZone",
                "route53:ListTagsForResource",
                "route53:ChangeResourceRecordSets",
                "route53:GetChange",
                "route53:ListResourceRecordSets"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::prod-levantine-terraform-bucket/thisper/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::prod-levantine-terraform-bucket",
            "Condition": {
                "StringLike": {
                    "s3:prefix": "thisper/*"
                }
            }
        }
    ]
}
EOF
}
