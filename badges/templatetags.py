# import the webapp module
from google.appengine.ext import webapp

import badges
import util_badges
from notifications import UserNotifier

import template_cached
register = template_cached.create_template_register()

@register.inclusion_tag("badges/notifications.html")
def badge_notifications():
    user_badges = UserNotifier.pop_for_current_user_data()["badges"]

    all_badges_dict = util_badges.all_badges_dict()
    for user_badge in user_badges:
        user_badge.badge = all_badges_dict.get(user_badge.badge_name)
        if user_badge.badge:
            user_badge.badge.is_owned = True

    user_badges = filter(lambda user_badge: user_badge.badge is not None, user_badges)

    if len(user_badges) > 1:
        user_badges = sorted(user_badges, reverse=True, key=lambda user_badge: user_badge.badge.points)[:badges.UserNotifier.NOTIFICATION_LIMIT]

    return {"user_badges": user_badges}

@register.inclusion_tag("badges/badge_counts.html")
def badge_counts(user_data):

    counts_dict = {}
    if user_data:
        counts_dict = util_badges.get_badge_counts(user_data)
    else:
        counts_dict = badges.BadgeCategory.empty_count_dict()

    sum_counts = 0
    for key in counts_dict:
        sum_counts += counts_dict[key]

    return {
        "sum": sum_counts,
        "bronze": counts_dict[badges.BadgeCategory.BRONZE],
        "silver": counts_dict[badges.BadgeCategory.SILVER],
        "gold": counts_dict[badges.BadgeCategory.GOLD],
        "platinum": counts_dict[badges.BadgeCategory.PLATINUM],
        "diamond": counts_dict[badges.BadgeCategory.DIAMOND],
        "master": counts_dict[badges.BadgeCategory.MASTER],
    }

@register.inclusion_tag("badges/badge_block.html")
def badge_block(badge, user_badge=None, show_frequency=False):

    if user_badge:
        badge.is_owned = True

    if badge.is_hidden():
        return {} # Don't render anything for this hidden badge

    frequency = None
    if show_frequency:
        frequency = badge.frequency()

    return {
        "badge": badge,
        "user_badge": user_badge,
        "extended_description": badge.safe_extended_description,
        "frequency": frequency
    }
