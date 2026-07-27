# Command Reference

Initial command surface:

```bash
bili init
bili doctor
bili login
bili status
bili me
bili logout
bili browser open
bili account list
bili config show
bili search "keyword"
bili read 1
bili detail BVxxxx
bili video info BVxxxx
bili video comments BVxxxx
bili danmaku BVxxxx
bili download BVxxxx --quality 360p
bili user info <mid>
bili user videos <mid> --limit 20
bili user followers <mid> --limit 20
bili user following <mid> --limit 20
bili user favorites <mid> --limit 20
bili profile <mid> --videos --limit 5
bili like BVxxxx
bili like BVxxxx --unlike --yes
bili coin BVxxxx --count 1
bili favorite folders
bili favorite add BVxxxx --folder <folder_id>
bili favorite remove BVxxxx --folder <folder_id>
bili watchlater add BVxxxx
bili follow <mid>
bili follow <mid> --unfollow
bili comment post BVxxxx "comment text"
bili comment delete BVxxxx <rpid>
bili trending
```

Every data command should support `--json` for agent consumption.

`user info` combines stable public profile APIs (`card`, relation stats, nav counts, privacy settings). Space list commands use Bilibili list APIs and may return structured `LOGIN_REQUIRED`, `CAPTCHA_REQUIRED`, or `RATE_LIMITED` errors when Bilibili blocks unauthenticated/risky access.

All write commands are safe by default: without `--yes`, they return a dry-run plan and append an audit event. `--dry-run` always wins when both `--dry-run` and `--yes` are provided.
