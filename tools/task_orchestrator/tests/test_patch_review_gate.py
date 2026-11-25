import hashlib, json, tempfile, unittest
from pathlib import Path
from tools.task_orchestrator.github_lease import make_lease
from tools.task_orchestrator.patch_artifacts import LocalPatchArtifactStore
from tools.task_orchestrator.patch_review_gate import PatchReviewGateError, validate_patch_for_human_review
from tools.task_orchestrator.tests.test_agent_contract import envelope
from tools.task_orchestrator.tests.test_patch_pipeline import completed_result, patch_text

REPO="majidbusy09-blip/jetconfig-vpn"; TASK="smart-routing-fix"
REPO_METADATA={"id":1349356614,"full_name":REPO,"html_url":"https://github.com/"+REPO,"default_branch":"main"}
BASE="a"*40; HEAD="b"*40; LOCK="c"*40; CLAIM="d"*16
NOW="2030-01-01T00:00:00Z"; EXPIRES="2030-01-01T02:00:00Z"

def body():
    task={"schema_version":1,"task_id":TASK,"goal":"Fix the scoped Smart Routing regression safely.",
      "capability":"bug_fix","risk":"medium","assigned_agent":"chatgpt",
      "allow":["lib/**","test/**"],"exclude":["lib/generated/**"],
      "scope_reason":"Bounded routing fix.",
      "verification_profiles":["python-tooling-tests","flutter-tests","flutter-analysis"]}
    return "<!-- jet-agent-task:v1 -->\n\n\x60\x60\x60json\n"+json.dumps(task)+"\n\x60\x60\x60"

def fixtures():
    env=envelope(); env["repository"].update(name=REPO,branch="agent/"+TASK,base_sha=BASE)
    issue_url="https://github.com/"+REPO+"/issues/42"
    record={"task_id":TASK,"goal":env["goal"],"capability_improved":env["capability"],
      "risk":env["risk"],"state":"prepared","assigned_agent":"chatgpt","source":"github-issue",
      "planned_checks":["python-tooling-tests","flutter-tests","flutter-analysis"],
      "scope":{"allowed":["lib/**","test/**"],"excluded":["lib/generated/**"],"reason":"Bounded routing fix."},
      "repository":{"origin":"https://github.com/"+REPO+".git","branch":"agent/"+TASK,"base_sha":BASE},
      "github_handoff":{"issue_number":42,"issue_url":issue_url,
        "issue_body_sha256":hashlib.sha256(body().encode()).hexdigest(),"owner":"chatgpt",
        "claim_id":CLAIM,"lease_expires_at":EXPIRES,"base_sha":BASE,
        "lock_branch":"agent-locks/"+TASK,"lock_commit":LOCK}}
    issue={"number":42,"state":"open","html_url":issue_url,"body":body(),"labels":[{"name":"agent-task"}]}
    lease=make_lease(task_id=TASK,owner="chatgpt",claim_id=CLAIM,base_sha=BASE,now=NOW,duration_minutes=120)
    return record,env,issue,lease

class PatchReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.store=LocalPatchArtifactStore(Path(self.tmp.name))
        self.record,self.env,self.issue,self.lease=fixtures()
        self.patch=patch_text(); self.store.store_patch(self.patch)
        self.result=completed_result(self.env,self.patch)
    def tearDown(self): self.tmp.cleanup()
    def gate(self,**changes):
        args=dict(record=self.record,envelope=self.env,result=self.result,store=self.store,
          issue_data=self.issue,lease_record=self.lease,lock_commit=LOCK,repository=REPO,
          repository_metadata=REPO_METADATA,
          branch="agent/"+TASK,head_sha=HEAD,base_is_ancestor=True,worktree_clean=True,now=NOW)
        args.update(changes); return validate_patch_for_human_review(**args)
    def test_current_scoped_patch_is_reviewable_but_never_applied(self):
        result=self.gate(); self.assertEqual(result["status"],"ready_for_human_review")
        self.assertFalse(result["applied"]); self.assertTrue(all(result["authorization"].values()))
    def test_rejects_closed_edited_or_unlabelled_issue(self):
        for issue in (dict(self.issue,state="closed"),dict(self.issue,body=self.issue["body"]+"x"),
                      dict(self.issue,labels=[])):
            with self.assertRaises(PatchReviewGateError): self.gate(issue_data=issue)
    def test_rejects_stale_released_or_expired_lease(self):
        with self.assertRaises(PatchReviewGateError): self.gate(lock_commit="e"*40)
        with self.assertRaises(PatchReviewGateError): self.gate(lease_record=dict(self.lease,status="released"))
        with self.assertRaises(PatchReviewGateError): self.gate(now="2030-01-01T03:00:00Z")
    def test_rejects_branch_base_or_dirty_workspace_drift(self):
        for args in ({"branch":"main"},{"base_is_ancestor":False},{"worktree_clean":False}):
            with self.subTest(args=args),self.assertRaises(PatchReviewGateError): self.gate(**args)
    def test_rejects_envelope_or_patch_scope_mismatch(self):
        with self.assertRaises(PatchReviewGateError): self.gate(envelope=dict(self.env,task_id="other-task"))
        bad=self.patch.replace("lib/routing_policy.dart","README.md")
        self.store.store_patch(bad); self.result=completed_result(self.env,bad)
        with self.assertRaises(PatchReviewGateError): self.gate()

if __name__=="__main__": unittest.main()
