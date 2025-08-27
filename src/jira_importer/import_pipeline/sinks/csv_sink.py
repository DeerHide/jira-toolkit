"""CSV sink: write Jira-ready CSV output."""
# NOTE, Jira CLoud: Some Jira Cloud users are affected by the historical "divide by 60" behavior. The fix (*60) will be implemented in this sink.
#   if config.get("jira.cloud.estimate.multiply_by_60", False):
#       row[estimate_index] = str(int(row[estimate_index]) * 60)
