#!/usr/bin/env python3
"""
Fellow Aiden OpenClaw Skill
CLI wrapper around the fellow-aiden Python library.
https://github.com/9b/fellow-aiden
"""

import argparse
import json
import os
import sys


def get_client():
    email = os.environ.get("FELLOW_EMAIL")
    password = os.environ.get("FELLOW_PASSWORD")

    if not email or not password:
        print(
            json.dumps(
                {
                    "error": "Missing credentials. Set FELLOW_EMAIL and FELLOW_PASSWORD environment variables."
                }
            )
        )
        sys.exit(1)

    try:
        from fellow_aiden import FellowAiden
        return FellowAiden(email, password)
    except ImportError:
        print(json.dumps({"error": "fellow-aiden library not installed. Run: pip3 install fellow-aiden"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Authentication failed: {str(e)}"}))
        sys.exit(1)


def output(data):
    print(json.dumps(data, indent=2, default=str))


# ─── INFO ────────────────────────────────────────────────────────────────────

def cmd_info(args):
    aiden = get_client()
    try:
        name = aiden.get_display_name()
        result = {"display_name": name}

        # Try to get extra device info if available
        try:
            details = aiden.get_device_details()
            result.update(details)
        except Exception:
            pass

        output(result)
    except Exception as e:
        output({"error": str(e)})


# ─── PROFILES ────────────────────────────────────────────────────────────────

def cmd_profiles_list(args):
    aiden = get_client()
    try:
        profiles = aiden.get_profiles()
        output({"profiles": profiles, "count": len(profiles)})
    except Exception as e:
        output({"error": str(e)})


def cmd_profiles_get(args):
    aiden = get_client()
    try:
        if args.id:
            profiles = aiden.get_profiles()
            match = next((p for p in profiles if p.get("id") == args.id), None)
            if match:
                output(match)
            else:
                output({"error": f"No profile found with id '{args.id}'"})
        elif args.title:
            profile = aiden.get_profile_by_title(args.title, fuzzy=args.fuzzy)
            if profile:
                output(profile)
            else:
                output({"error": f"No profile found matching '{args.title}'"})
        else:
            output({"error": "Provide --id or --title"})
    except Exception as e:
        output({"error": str(e)})


def cmd_profiles_create(args):
    aiden = get_client()
    try:
        # Parse temperature lists
        ss_temps = [int(t.strip()) for t in args.ss_temps.split(",")] if args.ss_temps else [96] * args.ss_pulses
        batch_temps = [int(t.strip()) for t in args.batch_temps.split(",")] if args.batch_temps else [96] * args.batch_pulses

        profile = {
            "profileType": 0,
            "title": args.title,
            "ratio": args.ratio,
            "bloomEnabled": args.bloom,
            "bloomRatio": args.bloom_ratio,
            "bloomDuration": args.bloom_duration,
            "bloomTemperature": args.bloom_temp,
            "ssPulsesEnabled": args.ss_pulses > 0,
            "ssPulsesNumber": args.ss_pulses,
            "ssPulsesInterval": args.ss_interval,
            "ssPulseTemperatures": ss_temps,
            "batchPulsesEnabled": args.batch_pulses > 0,
            "batchPulsesNumber": args.batch_pulses,
            "batchPulsesInterval": args.batch_interval,
            "batchPulseTemperatures": batch_temps,
        }

        result = aiden.create_profile(profile)
        output({"success": True, "message": f"Profile '{args.title}' created.", "result": result})
    except Exception as e:
        output({"error": str(e)})


def cmd_profiles_delete(args):
    aiden = get_client()
    try:
        if args.id:
            aiden.delete_profile_by_id(args.id)
            output({"success": True, "message": f"Profile '{args.id}' deleted."})
        elif args.title:
            profile = aiden.get_profile_by_title(args.title, fuzzy=args.fuzzy)
            if not profile:
                output({"error": f"No profile found matching '{args.title}'"})
                return
            pid = profile["id"]
            aiden.delete_profile_by_id(pid)
            output({"success": True, "message": f"Profile '{profile.get('title', pid)}' (id: {pid}) deleted."})
        else:
            output({"error": "Provide --id or --title"})
    except Exception as e:
        output({"error": str(e)})


def cmd_profiles_import(args):
    aiden = get_client()
    try:
        result = aiden.create_profile_from_link(args.url)
        output({"success": True, "message": f"Profile imported from {args.url}", "result": result})
    except Exception as e:
        output({"error": str(e)})


def cmd_profiles_share(args):
    aiden = get_client()
    try:
        pid = args.id
        if not pid and args.title:
            profile = aiden.get_profile_by_title(args.title, fuzzy=args.fuzzy)
            if not profile:
                output({"error": f"No profile found matching '{args.title}'"})
                return
            pid = profile["id"]

        if not pid:
            output({"error": "Provide --id or --title"})
            return

        link = aiden.generate_share_link(pid)
        output({"success": True, "share_url": link, "profile_id": pid})
    except Exception as e:
        output({"error": str(e)})


# ─── SCHEDULES ───────────────────────────────────────────────────────────────

def cmd_schedules_list(args):
    aiden = get_client()
    try:
        schedules = aiden.get_schedules()
        output({"schedules": schedules, "count": len(schedules)})
    except Exception as e:
        output({"error": str(e)})


def cmd_schedules_create(args):
    aiden = get_client()
    try:
        # Parse day names → [sun, mon, tue, wed, thu, fri, sat] boolean list
        day_names = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
        requested = [d.strip().lower()[:3] for d in args.days.split(",")]
        days_bools = [d in requested for d in day_names]

        # Parse HH:MM time → seconds since midnight
        hh, mm = map(int, args.time.split(":"))
        seconds_from_midnight = hh * 3600 + mm * 60

        schedule = {
            "days": days_bools,
            "secondFromStartOfTheDay": seconds_from_midnight,
            "enabled": True,
            "amountOfWater": args.water,
            "profileId": args.profile_id,
        }

        result = aiden.create_schedule(schedule)
        output({
            "success": True,
            "message": f"Schedule created: {args.days} at {args.time}, {args.water}ml, profile {args.profile_id}",
            "result": result,
        })
    except Exception as e:
        output({"error": str(e)})


def cmd_schedules_delete(args):
    aiden = get_client()
    try:
        aiden.delete_schedule_by_id(args.id)
        output({"success": True, "message": f"Schedule '{args.id}' deleted."})
    except Exception as e:
        output({"error": str(e)})


# ─── ARG PARSING ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fellow Aiden OpenClaw Skill — control your smart coffee brewer"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # info
    sub.add_parser("info", help="Show brewer display name and details")

    # profiles
    p_profiles = sub.add_parser("profiles", help="Manage brew profiles")
    p_profiles_sub = p_profiles.add_subparsers(dest="profiles_cmd", required=True)

    p_profiles_sub.add_parser("list", help="List all profiles")

    p_get = p_profiles_sub.add_parser("get", help="Get a profile by id or title")
    p_get.add_argument("--id", help="Profile ID (e.g. p0)")
    p_get.add_argument("--title", help="Profile title")
    p_get.add_argument("--fuzzy", action="store_true", help="Fuzzy title match")

    p_create = p_profiles_sub.add_parser("create", help="Create a new brew profile")
    p_create.add_argument("--title", required=True, help="Profile name")
    p_create.add_argument("--ratio", type=int, default=16, help="Water-to-coffee ratio (default: 16)")
    p_create.add_argument("--bloom", action="store_true", default=True, help="Enable bloom phase (default: on)")
    p_create.add_argument("--no-bloom", dest="bloom", action="store_false")
    p_create.add_argument("--bloom-ratio", type=int, default=2, help="Bloom water ratio (default: 2)")
    p_create.add_argument("--bloom-duration", type=int, default=30, help="Bloom duration in seconds (default: 30)")
    p_create.add_argument("--bloom-temp", type=int, default=96, help="Bloom temperature °C (default: 96)")
    p_create.add_argument("--ss-pulses", type=int, default=3, help="Number of slow-speed pulses (default: 3)")
    p_create.add_argument("--ss-interval", type=int, default=20, help="SS pulse interval seconds (default: 20)")
    p_create.add_argument("--ss-temps", help='SS pulse temps, comma-separated (e.g. "96,97,98")')
    p_create.add_argument("--batch-pulses", type=int, default=2, help="Number of batch pulses (default: 2)")
    p_create.add_argument("--batch-interval", type=int, default=30, help="Batch pulse interval seconds (default: 30)")
    p_create.add_argument("--batch-temps", help='Batch pulse temps, comma-separated (e.g. "96,97")')

    p_delete = p_profiles_sub.add_parser("delete", help="Delete a profile")
    p_delete.add_argument("--id", help="Profile ID")
    p_delete.add_argument("--title", help="Profile title")
    p_delete.add_argument("--fuzzy", action="store_true", help="Fuzzy title match")

    p_import = p_profiles_sub.add_parser("import", help="Import a profile from a brew.link URL")
    p_import.add_argument("--url", required=True, help="brew.link share URL (e.g. https://brew.link/p/ws98)")

    p_share = p_profiles_sub.add_parser("share", help="Generate a brew.link share URL for a profile")
    p_share.add_argument("--id", help="Profile ID")
    p_share.add_argument("--title", help="Profile title")
    p_share.add_argument("--fuzzy", action="store_true", help="Fuzzy title match")

    # schedules
    p_schedules = sub.add_parser("schedules", help="Manage brew schedules")
    p_schedules_sub = p_schedules.add_subparsers(dest="schedules_cmd", required=True)

    p_schedules_sub.add_parser("list", help="List all schedules")

    p_sched_create = p_schedules_sub.add_parser("create", help="Create a brew schedule")
    p_sched_create.add_argument(
        "--days", required=True,
        help='Comma-separated days (e.g. "mon,tue,wed,thu,fri" or "sun,sat")'
    )
    p_sched_create.add_argument(
        "--time", required=True,
        help="Brew time in HH:MM 24h format (e.g. 07:30)"
    )
    p_sched_create.add_argument("--water", type=int, required=True, help="Water amount in ml (150–1500)")
    p_sched_create.add_argument("--profile-id", required=True, help="Profile ID to use (e.g. p2)")

    p_sched_delete = p_schedules_sub.add_parser("delete", help="Delete a schedule")
    p_sched_delete.add_argument("--id", required=True, help="Schedule ID (e.g. s0)")

    args = parser.parse_args()

    dispatch = {
        "info": cmd_info,
        "profiles": {
            "list": cmd_profiles_list,
            "get": cmd_profiles_get,
            "create": cmd_profiles_create,
            "delete": cmd_profiles_delete,
            "import": cmd_profiles_import,
            "share": cmd_profiles_share,
        },
        "schedules": {
            "list": cmd_schedules_list,
            "create": cmd_schedules_create,
            "delete": cmd_schedules_delete,
        },
    }

    if args.command == "profiles":
        dispatch["profiles"][args.profiles_cmd](args)
    elif args.command == "schedules":
        dispatch["schedules"][args.schedules_cmd](args)
    else:
        dispatch[args.command](args)


if __name__ == "__main__":
    main()
