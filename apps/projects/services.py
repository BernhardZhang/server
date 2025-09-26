from django.db import models
from django.contrib.auth import get_user_model
from .models import Project, ProjectMembership, ProjectRevenue, ProjectLog, MemberRecruitment
from apps.tasks.models import Task
from apps.voting.models import RatingSession, Vote
import json
from datetime import datetime

User = get_user_model()

class ProjectDetailsService:
    """项目详情数据收集和导出服务"""

    @staticmethod
    def collect_project_details(project_id):
        """收集项目的完整详情数据"""
        try:
            project = Project.objects.get(id=project_id)

            # 收集项目基本信息
            project_info = ProjectDetailsService._get_project_basic_info(project)

            # 收集项目成员信息
            members_info = ProjectDetailsService._get_project_members(project)

            # 收集项目任务信息
            tasks_info = ProjectDetailsService._get_project_tasks(project)

            # 收集项目收益信息
            revenue_info = ProjectDetailsService._get_project_revenue(project)

            # 收集项目日志信息
            logs_info = ProjectDetailsService._get_project_logs(project)

            # 收集项目评分信息
            rating_info = ProjectDetailsService._get_project_ratings(project)

            # 收集项目招募信息
            recruitment_info = ProjectDetailsService._get_project_recruitment(project)

            # 收集项目投票信息
            voting_info = ProjectDetailsService._get_project_voting(project)

            # 收集成员申请信息
            applications_info = ProjectDetailsService._get_project_applications(project)

            # 收集功分信息
            merit_info = ProjectDetailsService._get_project_merit(project)

            # 组装完整的项目详情（先不包含统计数据）
            project_details = {
                'project_info': project_info,
                'members': members_info,
                'tasks': tasks_info,
                'revenue': revenue_info,
                'logs': logs_info,
                'ratings': rating_info,
                'recruitment': recruitment_info,
                'applications': applications_info,
                'voting': voting_info,
                'merit': merit_info,
                'generated_at': datetime.now().isoformat()
            }

            # 收集项目统计分析数据（基于已收集的数据）
            statistics_info = ProjectDetailsService._get_project_statistics(project_details)
            project_details['statistics'] = statistics_info

            return project_details

        except Project.DoesNotExist:
            return None

    @staticmethod
    def _get_project_basic_info(project):
        """获取项目基本信息"""
        return {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'project_type': project.get_project_type_display(),
            'status': project.get_status_display(),
            'progress': project.progress,
            'calculated_progress': project.calculated_progress,
            'tags': project.tag_list,
            'total_investment': float(project.total_investment),
            'valuation': float(project.valuation),
            'funding_rounds': project.funding_rounds,
            'is_public': project.is_public,
            'is_active': project.is_active,  # 新增：项目活跃状态
            'member_count': project.member_count,
            'start_date': project.start_date.isoformat() if project.start_date else None,
            'end_date': project.end_date.isoformat() if project.end_date else None,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
            # 新增：邀请码相关信息
            'invite_code': project.invite_code,
            'invite_code_enabled': project.invite_code_enabled,
            'invite_code_expires_at': project.invite_code_expires_at.isoformat() if project.invite_code_expires_at else None,
            'is_invite_code_valid': project.is_invite_code_valid(),
            'owner': {
                'id': project.owner.id,
                'username': project.owner.username,
                'first_name': project.owner.first_name,
                'last_name': project.owner.last_name,
            }
        }

    @staticmethod
    def _get_project_members(project):
        """获取项目成员信息"""
        memberships = ProjectMembership.objects.filter(
            project=project, is_active=True
        ).select_related('user')

        members = []
        for membership in memberships:
            user = membership.user
            member_info = {
                'user_id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': membership.get_role_display(),
                'contribution_percentage': float(membership.contribution_percentage),
                'equity_percentage': float(membership.equity_percentage),
                'investment_amount': float(membership.investment_amount),
                'contribution_description': membership.contribution_description,
                'join_date': membership.join_date.isoformat(),
            }
            members.append(member_info)

        return members

    @staticmethod
    def _get_project_tasks(project):
        """获取项目任务信息（包含所有关联数据）"""
        from apps.tasks.models import (
            Task, TaskComment, TaskAttachment, TaskEvaluation, TaskLog,
            TaskUserLog, TaskAssignment, TaskContributionRecord, TaskTeamMeritResult
        )

        tasks = Task.objects.filter(project=project).select_related(
            'creator', 'assignee'
        ).prefetch_related(
            'comments__author',
            'attachments'
        )

        tasks_data = []
        for task in tasks:
            # 获取任务评论
            comments = []
            for comment in task.comments.all():
                comments.append({
                    'id': comment.id,
                    'author': comment.author.username,
                    'author_name': f"{comment.author.first_name} {comment.author.last_name}".strip(),
                    'content': comment.content,
                    'created_at': comment.created_at.isoformat(),
                })

            # 获取任务附件
            attachments = []
            for attachment in task.attachments.all():
                attachments.append({
                    'id': attachment.id,
                    'filename': attachment.filename,
                    'file_type': attachment.get_file_type_display() if hasattr(attachment, 'get_file_type_display') else attachment.file_type,
                    'file_size': attachment.file_size,
                    'uploaded_by': attachment.uploaded_by.username,
                    'uploaded_at': attachment.uploaded_at.isoformat(),
                    'file_url': attachment.file.url if attachment.file else None,
                })

            # 获取任务分配（参与成员）
            assignments = []
            try:
                for assignment in TaskAssignment.objects.filter(task=task):
                    assignments.append({
                        'user': assignment.user.username,
                        'user_name': f"{assignment.user.first_name} {assignment.user.last_name}".strip(),
                        'role_weight': float(assignment.role_weight) if hasattr(assignment, 'role_weight') else 1.0,
                        'contribution_percentage': float(assignment.contribution_percentage) if hasattr(assignment, 'contribution_percentage') else 0.0,
                        'assigned_at': assignment.created_at.isoformat() if hasattr(assignment, 'created_at') else None,
                    })
            except:
                pass

            # 获取任务评估记录
            evaluations = []
            try:
                for evaluation in TaskEvaluation.objects.filter(task=task):
                    evaluations.append({
                        'id': evaluation.id,
                        'evaluator': evaluation.evaluator.username,
                        'score_type': evaluation.get_score_type_display(),
                        'score': float(evaluation.score),
                        'feedback': evaluation.feedback,
                        'evaluation_date': evaluation.created_at.isoformat(),
                    })
            except:
                pass

            # 获取任务操作日志
            task_logs = []
            try:
                for log in TaskLog.objects.filter(task=task)[:10]:  # 只取最近10条
                    task_logs.append({
                        'id': log.id,
                        'action': log.get_action_display() if hasattr(log, 'get_action_display') else log.action,
                        'user': log.user.username,
                        'description': log.description,
                        'old_value': log.old_value if hasattr(log, 'old_value') else None,
                        'new_value': log.new_value if hasattr(log, 'new_value') else None,
                        'created_at': log.created_at.isoformat(),
                    })
            except:
                pass

            # 获取用户工作日志
            user_logs = []
            try:
                for user_log in TaskUserLog.objects.filter(task=task):
                    user_logs.append({
                        'id': user_log.id,
                        'author': user_log.author.username,
                        'log_type': user_log.get_log_type_display(),
                        'title': user_log.title,
                        'content': user_log.content,
                        'hours_spent': float(user_log.hours_spent) if user_log.hours_spent else 0.0,
                        'created_at': user_log.created_at.isoformat(),
                    })
            except:
                pass

            # 获取功分计算结果
            merit_results = []
            try:
                merit_results_qs = TaskTeamMeritResult.objects.filter(
                    calculation__task=task
                )
                for result in merit_results_qs:
                    merit_results.append({
                        'user': result.user.username,
                        'function_score': float(result.function_score),
                        'final_score': float(result.final_score),
                        'contribution_percentage': float(result.contribution_percentage),
                        'calculation_date': result.calculation.created_at.isoformat() if result.calculation else None,
                    })
            except:
                pass

            task_info = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.get_status_display(),
                'priority': task.get_priority_display(),
                'progress': task.progress,
                'is_public': task.is_public,
                'is_available_for_claim': task.is_available_for_claim,
                'estimated_hours': float(task.estimated_hours) if task.estimated_hours else None,
                'actual_hours': float(task.actual_hours) if task.actual_hours else None,
                'system_score': float(task.system_score),
                'function_score': float(task.function_score),
                'time_coefficient': float(task.time_coefficient),
                'weight_coefficient': float(task.weight_coefficient) if hasattr(task, 'weight_coefficient') else 1.0,
                'tags': task.tag_list if hasattr(task, 'tag_list') else [],
                'category': task.category,
                'is_overdue': task.is_overdue if hasattr(task, 'is_overdue') else False,
                'start_date': task.start_date.isoformat() if task.start_date else None,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'completion_date': task.completion_date.isoformat() if task.completion_date else None,
                'creator': {
                    'username': task.creator.username,
                    'name': f"{task.creator.first_name} {task.creator.last_name}".strip()
                },
                'assignee': {
                    'username': task.assignee.username,
                    'name': f"{task.assignee.first_name} {task.assignee.last_name}".strip()
                } if task.assignee else None,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                # 关联数据
                'comments': comments,
                'attachments': attachments,
                'assignments': assignments,
                'evaluations': evaluations,
                'task_logs': task_logs,
                'user_logs': user_logs,
                'merit_results': merit_results,
                # 统计信息
                'comments_count': len(comments),
                'attachments_count': len(attachments),
                'participants_count': len(assignments),
            }
            tasks_data.append(task_info)

        return {
            'total_count': len(tasks_data),
            'status_summary': ProjectDetailsService._get_task_status_summary(tasks),
            'priority_summary': ProjectDetailsService._get_task_priority_summary(tasks),
            'category_summary': ProjectDetailsService._get_task_category_summary(tasks),
            'overdue_count': len([t for t in tasks if hasattr(t, 'is_overdue') and t.is_overdue]),
            'total_estimated_hours': sum([float(t.estimated_hours or 0) for t in tasks]),
            'total_actual_hours': sum([float(t.actual_hours or 0) for t in tasks]),
            'total_system_score': sum([float(t.system_score) for t in tasks]),
            'total_function_score': sum([float(t.function_score) for t in tasks]),
            'tasks': tasks_data
        }

    @staticmethod
    def _get_task_status_summary(tasks):
        """获取任务状态汇总"""
        status_counts = {}
        for task in tasks:
            status = task.get_status_display()
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts

    @staticmethod
    def _get_task_priority_summary(tasks):
        """获取任务优先级汇总"""
        priority_counts = {}
        for task in tasks:
            priority = task.get_priority_display()
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        return priority_counts

    @staticmethod
    def _get_task_category_summary(tasks):
        """获取任务分类汇总"""
        category_counts = {}
        for task in tasks:
            category = task.category or '未分类'
            category_counts[category] = category_counts.get(category, 0) + 1
        return category_counts

    @staticmethod
    def _get_project_revenue(project):
        """获取项目收益信息"""
        revenues = ProjectRevenue.objects.filter(project=project).select_related('recorded_by')

        revenue_data = []
        total_amount = 0
        total_net_amount = 0

        for revenue in revenues:
            # 获取收益分配详情
            distributions = []
            for distribution in revenue.distributions.all():
                distributions.append({
                    'id': distribution.id,
                    'member': distribution.member.username,
                    'member_name': f"{distribution.member.first_name} {distribution.member.last_name}".strip(),
                    'amount': float(distribution.amount),
                    'equity_percentage_at_time': float(distribution.equity_percentage_at_time),
                    'is_paid': distribution.is_paid,
                    'paid_at': distribution.paid_at.isoformat() if distribution.paid_at else None,
                    'payment_method': distribution.payment_method,
                    'payment_reference': distribution.payment_reference,
                    'created_at': distribution.created_at.isoformat(),
                })

            revenue_info = {
                'id': revenue.id,
                'revenue_type': revenue.get_revenue_type_display(),
                'amount': float(revenue.amount),
                'net_amount': float(revenue.net_amount),
                'associated_costs': float(revenue.associated_costs),
                'description': revenue.description,
                'source': revenue.source,
                'revenue_date': revenue.revenue_date.isoformat(),
                'is_distributed': revenue.is_distributed,
                'distribution_date': revenue.distribution_date.isoformat() if revenue.distribution_date else None,
                'recorded_by': revenue.recorded_by.username,
                'created_at': revenue.created_at.isoformat(),
                'distributions': distributions,  # 新增：分配详情
            }
            revenue_data.append(revenue_info)
            total_amount += float(revenue.amount)
            total_net_amount += float(revenue.net_amount)

        return {
            'total_revenue': total_amount,
            'total_net_revenue': total_net_amount,
            'revenue_count': len(revenue_data),
            'revenues': revenue_data
        }

    @staticmethod
    def _get_project_logs(project):
        """获取项目日志信息（包含关联数据）"""
        from apps.tasks.models import Task

        logs = ProjectLog.objects.filter(project=project).select_related(
            'user', 'related_user'
        ).prefetch_related().order_by('-created_at')[:200]  # 增加到200条

        logs_data = []
        log_type_summary = {}
        user_activity_summary = {}
        daily_activity = {}

        for log in logs:
            # 关联任务信息（如果有的话）
            related_task_info = None
            if hasattr(log, 'related_task') and log.related_task:
                try:
                    task = log.related_task
                    related_task_info = {
                        'id': task.id,
                        'title': task.title,
                        'status': task.get_status_display(),
                        'assignee': task.assignee.username if task.assignee else None,
                    }
                except:
                    pass

            # 解析元数据
            metadata_info = {}
            if log.metadata:
                metadata_info = log.metadata

            # 解析变更数据
            changes_info = {}
            if log.changes:
                changes_info = log.changes

            # 用户IP和地理位置信息
            location_info = {}
            if log.ip_address:
                location_info['ip_address'] = log.ip_address
                # 这里可以添加IP地理位置解析逻辑

            # 用户代理信息
            user_agent_info = {}
            if log.user_agent:
                user_agent_info['user_agent'] = log.user_agent
                # 这里可以添加用户代理解析逻辑（浏览器、操作系统等）

            log_info = {
                'id': log.id,
                'log_type': log.get_log_type_display(),
                'log_type_code': log.log_type,
                'title': log.title,
                'description': log.description,
                'user': log.user.username,
                'user_name': f"{log.user.first_name} {log.user.last_name}".strip(),
                'user_id': log.user.id,
                'action_method': log.action_method,
                'action_function': log.action_function,
                'related_user': log.related_user.username if log.related_user else None,
                'related_user_name': f"{log.related_user.first_name} {log.related_user.last_name}".strip() if log.related_user else None,
                'related_user_id': log.related_user.id if log.related_user else None,
                'related_task': related_task_info,
                'changes': changes_info,
                'metadata': metadata_info,
                'location_info': location_info,
                'user_agent_info': user_agent_info,
                'created_at': log.created_at.isoformat(),
                'created_date': log.created_at.date().isoformat(),
                'created_time': log.created_at.time().isoformat(),
            }
            logs_data.append(log_info)

            # 统计日志类型
            log_type = log.get_log_type_display()
            log_type_summary[log_type] = log_type_summary.get(log_type, 0) + 1

            # 统计用户活动
            user_key = log.user.username
            if user_key not in user_activity_summary:
                user_activity_summary[user_key] = {
                    'user_name': f"{log.user.first_name} {log.user.last_name}".strip(),
                    'total_activities': 0,
                    'activity_types': {},
                    'first_activity': log.created_at.isoformat(),
                    'last_activity': log.created_at.isoformat(),
                }

            user_activity_summary[user_key]['total_activities'] += 1
            user_activity_summary[user_key]['activity_types'][log_type] = user_activity_summary[user_key]['activity_types'].get(log_type, 0) + 1

            # 更新最早和最晚活动时间
            if log.created_at.isoformat() < user_activity_summary[user_key]['first_activity']:
                user_activity_summary[user_key]['first_activity'] = log.created_at.isoformat()
            if log.created_at.isoformat() > user_activity_summary[user_key]['last_activity']:
                user_activity_summary[user_key]['last_activity'] = log.created_at.isoformat()

            # 统计每日活动
            date_key = log.created_at.date().isoformat()
            if date_key not in daily_activity:
                daily_activity[date_key] = {
                    'total_activities': 0,
                    'unique_users': set(),
                    'activity_types': {}
                }
            daily_activity[date_key]['total_activities'] += 1
            daily_activity[date_key]['unique_users'].add(log.user.username)
            daily_activity[date_key]['activity_types'][log_type] = daily_activity[date_key]['activity_types'].get(log_type, 0) + 1

        # 处理每日活动数据（转换set为count）
        daily_activity_processed = {}
        for date, data in daily_activity.items():
            daily_activity_processed[date] = {
                'total_activities': data['total_activities'],
                'unique_users_count': len(data['unique_users']),
                'activity_types': data['activity_types']
            }

        # 按用户活跃度排序
        sorted_user_activity = dict(sorted(
            user_activity_summary.items(),
            key=lambda x: x[1]['total_activities'],
            reverse=True
        ))

        # 最近活跃用户（最近7天）
        from datetime import datetime, timedelta
        recent_date = datetime.now() - timedelta(days=7)
        recent_active_users = {}
        for log in logs_data:
            if datetime.fromisoformat(log['created_at'].replace('Z', '+00:00')).replace(tzinfo=None) > recent_date:
                user = log['user']
                if user not in recent_active_users:
                    recent_active_users[user] = {
                        'user_name': log['user_name'],
                        'recent_activities': 0,
                        'latest_activity': log['created_at']
                    }
                recent_active_users[user]['recent_activities'] += 1

        return {
            'recent_logs_count': len(logs_data),
            'logs': logs_data,
            'log_statistics': {
                'log_type_summary': log_type_summary,
                'user_activity_summary': sorted_user_activity,
                'daily_activity': daily_activity_processed,
                'recent_active_users': recent_active_users,
                'total_unique_users': len(user_activity_summary),
                'most_active_user': max(user_activity_summary.items(), key=lambda x: x[1]['total_activities'])[0] if user_activity_summary else None,
                'most_common_activity': max(log_type_summary.items(), key=lambda x: x[1])[0] if log_type_summary else None,
                'activity_peak_date': max(daily_activity_processed.items(), key=lambda x: x[1]['total_activities'])[0] if daily_activity_processed else None,
            }
        }

    @staticmethod
    def _get_project_ratings(project):
        """获取项目评分信息"""
        try:
            rating_sessions = RatingSession.objects.filter(project=project)

            sessions_data = []
            for session in rating_sessions:
                session_info = {
                    'id': session.id,
                    'session_name': session.session_name,
                    'status': session.get_status_display(),
                    'start_date': session.start_date.isoformat() if session.start_date else None,
                    'end_date': session.end_date.isoformat() if session.end_date else None,
                    'created_at': session.created_at.isoformat(),
                }
                sessions_data.append(session_info)

            return {
                'rating_sessions_count': len(sessions_data),
                'sessions': sessions_data
            }
        except:
            return {'rating_sessions_count': 0, 'sessions': []}

    @staticmethod
    def _get_project_recruitment(project):
        """获取项目招募信息"""
        recruitments = MemberRecruitment.objects.filter(project=project).select_related('created_by')

        recruitment_data = []
        for recruitment in recruitments:
            recruitment_info = {
                'id': recruitment.id,
                'title': recruitment.title,
                'description': recruitment.description,
                'required_skills': recruitment.required_skills,
                'skill_level_required': recruitment.get_skill_level_required_display(),
                'positions_needed': recruitment.positions_needed,
                'positions_filled': recruitment.positions_filled,
                'work_type': recruitment.get_work_type_display(),
                'expected_commitment': recruitment.expected_commitment,
                'salary_range': recruitment.salary_range,
                'equity_percentage_min': float(recruitment.equity_percentage_min),
                'equity_percentage_max': float(recruitment.equity_percentage_max),
                'status': recruitment.get_status_display(),
                'deadline': recruitment.deadline.isoformat() if recruitment.deadline else None,
                'created_by': recruitment.created_by.username,
                'created_at': recruitment.created_at.isoformat(),
                'is_active': recruitment.is_active,
                'application_count': recruitment.application_count,
            }
            recruitment_data.append(recruitment_info)

        return {
            'recruitment_count': len(recruitment_data),
            'recruitments': recruitment_data
        }

    @staticmethod
    def _get_project_voting(project):
        """获取项目投票信息（包含完整关联数据）"""
        try:
            from apps.voting.models import Vote, VotingRound, RatingSession, Rating

            # 获取与项目相关的投票记录（包含轮次信息）
            votes = Vote.objects.filter(target_project=project).select_related(
                'voter', 'target_user', 'voting_round'
            ).prefetch_related('voting_round')

            voting_data = []
            total_vote_amount = 0
            vote_rounds_data = {}  # 按轮次分组

            for vote in votes:
                # 收集投票轮次信息
                round_info = None
                if vote.voting_round:
                    round_key = vote.voting_round.id
                    if round_key not in vote_rounds_data:
                        vote_rounds_data[round_key] = {
                            'id': vote.voting_round.id,
                            'name': vote.voting_round.name,
                            'description': vote.voting_round.description,
                            'start_time': vote.voting_round.start_time.isoformat(),
                            'end_time': vote.voting_round.end_time.isoformat(),
                            'is_active': vote.voting_round.is_active,
                            'is_self_evaluation_open': vote.voting_round.is_self_evaluation_open,
                            'max_self_investment': float(vote.voting_round.max_self_investment),
                            'votes_count': 0,
                            'total_amount': 0,
                        }
                    vote_rounds_data[round_key]['votes_count'] += 1
                    vote_rounds_data[round_key]['total_amount'] += float(vote.amount)

                vote_info = {
                    'id': vote.id,
                    'voter': vote.voter.username,
                    'voter_name': f"{vote.voter.first_name} {vote.voter.last_name}".strip(),
                    'target_type': 'project',
                    'target_name': project.name,
                    'vote_type': vote.get_vote_type_display(),
                    'amount': float(vote.amount),
                    'is_paid': vote.is_paid,
                    'payment_transaction_id': vote.payment_transaction_id,
                    'voting_round': vote.voting_round.name if vote.voting_round else '无轮次',
                    'voting_round_id': vote.voting_round.id if vote.voting_round else None,
                    'created_at': vote.created_at.isoformat(),
                }
                voting_data.append(vote_info)
                total_vote_amount += float(vote.amount)

            # 获取项目评分活动（包含评分详情）
            rating_sessions = RatingSession.objects.filter(project=project).prefetch_related(
                'rating_records__rater',
                'rating_records__target',
                'selected_members'
            )
            rating_sessions_data = []

            for session in rating_sessions:
                ratings = session.rating_records.all()
                ratings_data = []

                # 计算评分统计
                total_ratings = len(ratings)
                average_score = sum([r.score for r in ratings]) / total_ratings if total_ratings > 0 else 0
                score_distribution = {}

                for rating in ratings:
                    # 评分分布统计
                    score_range = f"{(rating.score//10)*10}-{(rating.score//10)*10+9}"
                    score_distribution[score_range] = score_distribution.get(score_range, 0) + 1

                    ratings_data.append({
                        'id': rating.id,
                        'rater': rating.rater.username,
                        'rater_name': f"{rating.rater.first_name} {rating.rater.last_name}".strip(),
                        'target': rating.target.username,
                        'target_name': f"{rating.target.first_name} {rating.target.last_name}".strip(),
                        'score': rating.score,
                        'remark': rating.remark,
                        'created_at': rating.created_at.isoformat(),
                        'updated_at': rating.updated_at.isoformat() if hasattr(rating, 'updated_at') else None,
                    })

                # 获取参与成员列表
                selected_members = []
                for member in session.selected_members.all():
                    selected_members.append({
                        'username': member.username,
                        'name': f"{member.first_name} {member.last_name}".strip(),
                        'ratings_given': len([r for r in ratings if r.rater == member]),
                        'ratings_received': len([r for r in ratings if r.target == member]),
                        'average_score_received': sum([r.score for r in ratings if r.target == member]) / len([r for r in ratings if r.target == member]) if len([r for r in ratings if r.target == member]) > 0 else 0,
                    })

                rating_sessions_data.append({
                    'id': session.id,
                    'theme': session.theme,
                    'description': session.description,
                    'status': session.get_status_display(),
                    'total_points': session.total_points,
                    'member_count': session.member_count,
                    'rating_count': session.rating_count,
                    'created_by': session.created_by.username,
                    'created_by_name': f"{session.created_by.first_name} {session.created_by.last_name}".strip(),
                    'created_at': session.created_at.isoformat(),
                    'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                    'selected_members': selected_members,
                    'ratings': ratings_data,
                    # 评分统计信息
                    'rating_statistics': {
                        'total_ratings': total_ratings,
                        'average_score': round(average_score, 2),
                        'score_distribution': score_distribution,
                        'participation_rate': (total_ratings / (session.member_count * (session.member_count - 1))) * 100 if session.member_count > 1 else 0,
                    }
                })

            # 投票轮次统计
            voting_rounds_list = list(vote_rounds_data.values())

            # 投票类型统计
            vote_type_summary = {}
            payment_summary = {'paid': 0, 'unpaid': 0}
            for vote in votes:
                vote_type = vote.get_vote_type_display()
                vote_type_summary[vote_type] = vote_type_summary.get(vote_type, 0) + 1
                if vote.is_paid:
                    payment_summary['paid'] += 1
                else:
                    payment_summary['unpaid'] += 1

            return {
                'total_vote_amount': total_vote_amount,
                'voting_count': len(voting_data),
                'votes': voting_data,
                'voting_rounds': voting_rounds_list,
                'vote_type_summary': vote_type_summary,
                'payment_summary': payment_summary,
                'rating_sessions_count': len(rating_sessions_data),
                'rating_sessions': rating_sessions_data,
                # 总体统计
                'voting_summary': {
                    'unique_voters': len(set([v['voter'] for v in voting_data])),
                    'average_vote_amount': total_vote_amount / len(voting_data) if len(voting_data) > 0 else 0,
                    'total_rounds': len(voting_rounds_list),
                    'active_rounds': len([r for r in voting_rounds_list if r['is_active']]),
                }
            }
        except Exception as e:
            print(f"获取投票信息失败: {e}")
            return {
                'total_vote_amount': 0,
                'voting_count': 0,
                'votes': [],
                'voting_rounds': [],
                'vote_type_summary': {},
                'payment_summary': {'paid': 0, 'unpaid': 0},
                'rating_sessions_count': 0,
                'rating_sessions': [],
                'voting_summary': {
                    'unique_voters': 0,
                    'average_vote_amount': 0,
                    'total_rounds': 0,
                    'active_rounds': 0,
                }
            }

    @staticmethod
    def _get_project_applications(project):
        """获取项目成员申请信息"""
        try:
            from .models import MemberApplication

            # 获取项目所有招募岗位的申请
            applications = MemberApplication.objects.filter(
                recruitment__project=project
            ).select_related('applicant', 'recruitment', 'reviewed_by')

            application_data = []
            for application in applications:
                application_info = {
                    'id': application.id,
                    'recruitment_title': application.recruitment.title,
                    'applicant': application.applicant.username,
                    'applicant_name': f"{application.applicant.first_name} {application.applicant.last_name}".strip(),
                    'cover_letter': application.cover_letter,
                    'skills': application.skills,
                    'experience': application.experience,
                    'portfolio_url': application.portfolio_url,
                    'expected_commitment': application.expected_commitment,
                    'status': application.get_status_display(),
                    'reviewed_by': application.reviewed_by.username if application.reviewed_by else None,
                    'review_notes': application.review_notes,
                    'reviewed_at': application.reviewed_at.isoformat() if application.reviewed_at else None,
                    'created_at': application.created_at.isoformat(),
                    'updated_at': application.updated_at.isoformat(),
                }
                application_data.append(application_info)

            # 统计申请状态
            status_counts = {}
            for app in applications:
                status = app.get_status_display()
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                'total_applications': len(application_data),
                'status_summary': status_counts,
                'applications': application_data
            }
        except Exception as e:
            print(f"获取申请信息失败: {e}")
            return {'total_applications': 0, 'status_summary': {}, 'applications': []}

    @staticmethod
    def _get_project_merit(project):
        """获取项目功分信息"""
        try:
            from apps.merit.models import ProjectMeritCalculation, MeritCalculationResult

            # 获取项目的功分计算记录
            calculations = ProjectMeritCalculation.objects.filter(project=project)
            # 修正查询：使用calculation__project而不是project
            results = MeritCalculationResult.objects.filter(calculation__project=project)

            merit_data = []
            total_points = 0

            # 从计算结果中获取功分数据
            for result in results:
                merit_info = {
                    'id': result.id,
                    'user': result.user.username if result.user else 'Unknown',
                    'points': float(result.total_team_points),  # 使用total_team_points
                    'reason': f"功分计算 - {result.calculation.name if hasattr(result.calculation, 'name') else '功分计算'}",
                    'awarded_by': '系统计算',
                    'created_at': result.created_at.isoformat() if hasattr(result, 'created_at') else None,
                }
                merit_data.append(merit_info)
                total_points += float(result.total_team_points)

            return {
                'total_merit_points': total_points,
                'merit_records_count': len(merit_data),
                'merits': merit_data
            }
        except Exception as e:
            print(f"获取功分信息失败: {e}")
            return {'total_merit_points': 0, 'merit_records_count': 0, 'merits': []}

    @staticmethod
    def _get_project_statistics(project_details):
        """生成项目综合统计分析数据"""
        from datetime import datetime, timedelta
        from decimal import Decimal

        try:
            # 基础统计
            basic_stats = {
                'total_members': len(project_details.get('members', [])),
                'total_tasks': project_details.get('tasks', {}).get('total_count', 0),
                'total_revenues': project_details.get('revenue', {}).get('revenue_count', 0),
                'total_logs': project_details.get('logs', {}).get('recent_logs_count', 0),
                'total_applications': project_details.get('applications', {}).get('total_applications', 0),
                'total_recruitments': project_details.get('recruitment', {}).get('recruitment_count', 0),
                'total_votes': project_details.get('voting', {}).get('voting_count', 0),
                'total_rating_sessions': project_details.get('voting', {}).get('rating_sessions_count', 0),
                'total_merit_points': project_details.get('merit', {}).get('total_merit_points', 0),
            }

            # 任务执行效率分析
            tasks_data = project_details.get('tasks', {})
            task_efficiency = {
                'completion_rate': 0,
                'average_progress': 0,
                'overdue_rate': 0,
                'efficiency_score': 0,
                'estimated_vs_actual_hours': {'ratio': 0, 'variance': 0},
            }

            if tasks_data.get('total_count', 0) > 0:
                tasks = tasks_data.get('tasks', [])
                completed_tasks = [t for t in tasks if t['status'] == '已完成']
                overdue_tasks = [t for t in tasks if t.get('is_overdue', False)]

                task_efficiency['completion_rate'] = len(completed_tasks) / len(tasks) * 100
                task_efficiency['average_progress'] = sum([t['progress'] for t in tasks]) / len(tasks)
                task_efficiency['overdue_rate'] = len(overdue_tasks) / len(tasks) * 100

                # 工时预估准确性分析
                tasks_with_hours = [t for t in tasks if t.get('estimated_hours') and t.get('actual_hours')]
                if tasks_with_hours:
                    estimated_total = sum([t['estimated_hours'] for t in tasks_with_hours])
                    actual_total = sum([t['actual_hours'] for t in tasks_with_hours])
                    if estimated_total > 0:
                        task_efficiency['estimated_vs_actual_hours']['ratio'] = actual_total / estimated_total
                        task_efficiency['estimated_vs_actual_hours']['variance'] = abs(actual_total - estimated_total) / estimated_total * 100

                # 综合效率得分 (0-100)
                task_efficiency['efficiency_score'] = (
                    task_efficiency['completion_rate'] * 0.4 +
                    task_efficiency['average_progress'] * 0.3 +
                    max(0, 100 - task_efficiency['overdue_rate']) * 0.3
                )

            # 财务健康度分析
            revenue_data = project_details.get('revenue', {})
            financial_health = {
                'total_revenue': revenue_data.get('total_revenue', 0),
                'total_net_revenue': revenue_data.get('total_net_revenue', 0),
                'profit_margin': 0,
                'revenue_per_member': 0,
                'revenue_growth_trend': 'stable',  # 需要历史数据分析
                'distribution_efficiency': 0,
            }

            if financial_health['total_revenue'] > 0:
                financial_health['profit_margin'] = (financial_health['total_net_revenue'] / financial_health['total_revenue']) * 100
                if basic_stats['total_members'] > 0:
                    financial_health['revenue_per_member'] = financial_health['total_revenue'] / basic_stats['total_members']

            # 分配效率分析
            distributed_count = 0
            total_revenue_records = len(revenue_data.get('revenues', []))
            if total_revenue_records > 0:
                for revenue in revenue_data.get('revenues', []):
                    if revenue.get('is_distributed'):
                        distributed_count += 1
                financial_health['distribution_efficiency'] = distributed_count / total_revenue_records * 100

            # 团队活跃度分析
            logs_data = project_details.get('logs', {})
            team_activity = {
                'activity_score': 0,
                'participation_rate': 0,
                'communication_frequency': 0,
                'collaboration_index': 0,
                'recent_activity_trend': 'stable',
            }

            if logs_data.get('log_statistics'):
                stats = logs_data['log_statistics']
                unique_active_users = stats.get('total_unique_users', 0)
                if basic_stats['total_members'] > 0:
                    team_activity['participation_rate'] = unique_active_users / basic_stats['total_members'] * 100

                # 通信频率 (每个活跃用户平均日志数)
                if unique_active_users > 0:
                    team_activity['communication_frequency'] = basic_stats['total_logs'] / unique_active_users

                # 协作指数基于多种互动类型的分布
                activity_types = stats.get('log_type_summary', {})
                collaborative_activities = ['成员加入', '任务分配', '评论添加', '评分创建', '投票参与']
                collab_count = sum([activity_types.get(act, 0) for act in collaborative_activities])
                if basic_stats['total_logs'] > 0:
                    team_activity['collaboration_index'] = collab_count / basic_stats['total_logs'] * 100

                # 综合活跃度得分
                team_activity['activity_score'] = (
                    team_activity['participation_rate'] * 0.4 +
                    min(100, team_activity['communication_frequency'] * 10) * 0.3 +
                    team_activity['collaboration_index'] * 0.3
                )

            # 投票评价分析
            voting_data = project_details.get('voting', {})
            voting_analysis = {
                'total_investment': voting_data.get('total_vote_amount', 0),
                'average_vote_amount': voting_data.get('voting_summary', {}).get('average_vote_amount', 0),
                'participation_diversity': voting_data.get('voting_summary', {}).get('unique_voters', 0),
                'payment_completion_rate': 0,
                'community_support_score': 0,
            }

            # 支付完成率
            payment_summary = voting_data.get('payment_summary', {})
            total_votes = payment_summary.get('paid', 0) + payment_summary.get('unpaid', 0)
            if total_votes > 0:
                voting_analysis['payment_completion_rate'] = payment_summary.get('paid', 0) / total_votes * 100

            # 社区支持分数
            if basic_stats['total_members'] > 0:
                voting_analysis['community_support_score'] = (
                    voting_analysis['participation_diversity'] / basic_stats['total_members'] * 50 +
                    min(50, voting_analysis['average_vote_amount'] * 100)  # 假设1元为满分
                )

            # 项目成熟度评估
            project_info = project_details.get('project_info', {})
            maturity_assessment = {
                'project_age_days': 0,
                'development_stage': 'startup',  # startup, growth, mature
                'risk_level': 'medium',  # low, medium, high
                'sustainability_score': 0,
                'growth_potential': 0,
            }

            # 计算项目年龄
            created_at = project_info.get('created_at')
            if created_at:
                project_start = datetime.fromisoformat(created_at.replace('Z', '+00:00')).replace(tzinfo=None)
                maturity_assessment['project_age_days'] = (datetime.now() - project_start).days

            # 发展阶段评估
            age_days = maturity_assessment['project_age_days']
            if age_days < 30:
                maturity_assessment['development_stage'] = 'startup'
            elif age_days < 180:
                maturity_assessment['development_stage'] = 'growth'
            else:
                maturity_assessment['development_stage'] = 'mature'

            # 可持续性评分 (基于多个维度)
            sustainability_factors = {
                'financial_health': min(100, financial_health['profit_margin']),
                'team_activity': team_activity['activity_score'],
                'task_efficiency': task_efficiency['efficiency_score'],
                'community_support': voting_analysis['community_support_score'],
            }

            maturity_assessment['sustainability_score'] = sum(sustainability_factors.values()) / len(sustainability_factors)

            # 风险等级评估
            risk_factors = [
                task_efficiency['overdue_rate'] > 30,  # 逾期率高
                team_activity['participation_rate'] < 50,  # 参与度低
                financial_health['profit_margin'] < 0,  # 亏损
                basic_stats['total_members'] < 3,  # 团队规模小
            ]

            risk_count = sum(risk_factors)
            if risk_count >= 3:
                maturity_assessment['risk_level'] = 'high'
            elif risk_count >= 2:
                maturity_assessment['risk_level'] = 'medium'
            else:
                maturity_assessment['risk_level'] = 'low'

            # 成长潜力评估
            growth_indicators = {
                'active_recruitment': basic_stats['total_recruitments'] > 0,
                'recent_activity': basic_stats['total_logs'] > 10,
                'positive_voting': voting_analysis['community_support_score'] > 50,
                'revenue_generation': financial_health['total_revenue'] > 0,
                'task_completion': task_efficiency['completion_rate'] > 60,
            }

            maturity_assessment['growth_potential'] = sum(growth_indicators.values()) / len(growth_indicators) * 100

            # 关键绩效指标 (KPIs)
            kpis = {
                'overall_health_score': 0,  # 综合健康度评分 (0-100)
                'efficiency_index': task_efficiency['efficiency_score'],
                'team_cohesion': team_activity['collaboration_index'],
                'financial_stability': financial_health['profit_margin'] if financial_health['profit_margin'] >= 0 else 0,
                'community_engagement': voting_analysis['community_support_score'],
                'growth_momentum': maturity_assessment['growth_potential'],
            }

            # 计算综合健康度评分
            kpi_weights = {
                'efficiency_index': 0.25,
                'team_cohesion': 0.20,
                'financial_stability': 0.20,
                'community_engagement': 0.20,
                'growth_momentum': 0.15,
            }

            kpis['overall_health_score'] = sum([
                kpis[key] * weight for key, weight in kpi_weights.items()
            ])

            # 改进建议
            recommendations = []

            if task_efficiency['completion_rate'] < 70:
                recommendations.append({
                    'area': '任务管理',
                    'priority': 'high',
                    'suggestion': '提高任务完成率，建议优化任务分配和跟进机制',
                    'expected_impact': '提升项目执行效率'
                })

            if team_activity['participation_rate'] < 60:
                recommendations.append({
                    'area': '团队协作',
                    'priority': 'medium',
                    'suggestion': '增加团队沟通和协作活动，提高成员参与度',
                    'expected_impact': '增强团队凝聚力'
                })

            if financial_health['profit_margin'] < 10:
                recommendations.append({
                    'area': '财务管理',
                    'priority': 'high',
                    'suggestion': '优化成本结构，提高盈利能力',
                    'expected_impact': '改善财务健康状况'
                })

            if voting_analysis['community_support_score'] < 40:
                recommendations.append({
                    'area': '社区建设',
                    'priority': 'medium',
                    'suggestion': '加强与社区的互动，提高项目知名度和支持度',
                    'expected_impact': '扩大项目影响力'
                })

            return {
                'basic_stats': basic_stats,
                'task_efficiency': task_efficiency,
                'financial_health': financial_health,
                'team_activity': team_activity,
                'voting_analysis': voting_analysis,
                'maturity_assessment': maturity_assessment,
                'kpis': kpis,
                'recommendations': recommendations,
                'analysis_timestamp': datetime.now().isoformat(),
                'data_freshness': {
                    'tasks_updated': project_details.get('tasks', {}).get('tasks', [{}])[0].get('updated_at') if project_details.get('tasks', {}).get('tasks') else None,
                    'logs_latest': project_details.get('logs', {}).get('logs', [{}])[0].get('created_at') if project_details.get('logs', {}).get('logs') else None,
                    'revenue_latest': project_details.get('revenue', {}).get('revenues', [{}])[0].get('created_at') if project_details.get('revenue', {}).get('revenues') else None,
                }
            }

        except Exception as e:
            print(f"生成项目统计分析失败: {e}")
            return {
                'basic_stats': {},
                'task_efficiency': {},
                'financial_health': {},
                'team_activity': {},
                'voting_analysis': {},
                'maturity_assessment': {},
                'kpis': {},
                'recommendations': [],
                'analysis_timestamp': datetime.now().isoformat(),
                'error': str(e)
            }

    @staticmethod
    def generate_structured_report(project_details):
        """将项目详情转换为结构化格式的报告，便于AI理解"""
        if not project_details:
            return {"error": "项目信息未找到"}

        project_info = project_details['project_info']

        # 构建结构化的项目报告
        structured_report = {
            "项目基本信息": {
                "项目名称": project_info['name'],
                "项目描述": project_info['description'],
                "项目类型": project_info['project_type'],
                "当前状态": project_info['status'],
                "项目进度": f"{project_info['progress']}%（手动设定）/ {project_info['calculated_progress']}%（系统计算）",
                "是否公开": "是" if project_info['is_public'] else "否",
                "项目标签": project_info['tags'] if project_info['tags'] else "无",
                "项目负责人": f"{project_info['owner']['username']} ({project_info['owner']['first_name']} {project_info['owner']['last_name']})",
                "成员总数": project_info['member_count'],
                "创建时间": project_info['created_at'][:10],
                "最后更新": project_info['updated_at'][:10]
            },

            "财务概况": {
                "总投资额": f"¥{project_info['total_investment']:,.2f}",
                "项目估值": f"¥{project_info['valuation']:,.2f}",
                "融资轮次": f"{project_info['funding_rounds']}轮",
                "项目收益": {
                    "总收益": f"¥{project_details['revenue']['total_revenue']:,.2f}",
                    "净收益": f"¥{project_details['revenue']['total_net_revenue']:,.2f}",
                    "收益记录数": project_details['revenue']['revenue_count']
                }
            },

            "团队信息": {
                "成员总数": len(project_details['members']),
                "成员详情": []
            },

            "任务执行情况": {
                "任务总数": project_details['tasks']['total_count'],
                "任务状态分布": project_details['tasks']['status_summary'],
                "关键任务": []
            },

            "投票评价情况": {
                "项目获得投票": {
                    "投票总金额": f"¥{project_details['voting'].get('total_vote_amount', 0):,.2f}",
                    "投票次数": project_details['voting']['voting_count'],
                    "投票详情": project_details['voting']['votes']
                },
                "评分活动": {
                    "评分活动数": project_details['voting']['rating_sessions_count'],
                    "评分详情": project_details['voting']['rating_sessions']
                }
            },

            "功分情况": {
                "总功分": f"{project_details['merit']['total_merit_points']:.2f}分",
                "功分记录数": project_details['merit']['merit_records_count'],
                "功分分布": []
            },

            "项目活跃度": {
                "最近活动数": project_details['logs']['recent_logs_count'],
                "主要活动类型": []
            },

            "招募情况": {
                "招募岗位数": project_details['recruitment']['recruitment_count'],
                "招募详情": project_details['recruitment']['recruitments']
            },

            "申请情况": {
                "申请总数": project_details['applications']['total_applications'],
                "申请状态分布": project_details['applications']['status_summary'],
                "申请详情": project_details['applications']['applications'][:10]  # 只显示前10个申请
            }
        }

        # 补充成员详情
        for member in project_details['members']:
            structured_report["团队信息"]["成员详情"].append({
                "姓名": f"{member['username']} ({member['first_name']} {member['last_name']})",
                "角色": member['role'],
                "贡献比例": f"{member['contribution_percentage']}%",
                "股份比例": f"{member['equity_percentage']}%",
                "投资金额": f"¥{member['investment_amount']:,.2f}",
                "加入时间": member['join_date'][:10],
                "贡献描述": member['contribution_description'] or "无"
            })

        # 补充关键任务信息（取前5个最重要的任务）
        tasks_sorted = sorted(project_details['tasks']['tasks'],
                             key=lambda x: (x['progress'], x['estimated_hours'] or 0),
                             reverse=True)[:5]
        for task in tasks_sorted:
            structured_report["任务执行情况"]["关键任务"].append({
                "任务名称": task['title'],
                "状态": task['status'],
                "进度": f"{task['progress']}%",
                "负责人": task['assignee']['username'] if task['assignee'] else "未分配",
                "预估工时": f"{task['estimated_hours'] or 0}小时",
                "截止日期": task['due_date'][:10] if task['due_date'] else "未设定"
            })

        # 补充功分分布
        for merit in project_details['merit']['merits']:
            structured_report["功分情况"]["功分分布"].append({
                "用户": merit['user'],
                "分数": f"{merit['points']:.2f}分",
                "原因": merit['reason'],
                "时间": merit['created_at'][:10] if merit['created_at'] else "未知"
            })

        # 补充活动类型统计
        activity_types = {}
        for log in project_details['logs']['logs']:
            activity_type = log['log_type']
            activity_types[activity_type] = activity_types.get(activity_type, 0) + 1

        structured_report["项目活跃度"]["主要活动类型"] = [
            {"类型": k, "次数": v} for k, v in sorted(activity_types.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # 添加生成时间
        structured_report["报告生成时间"] = project_details['generated_at'][:19]

        return structured_report

    @staticmethod
    def generate_markdown_report(project_details):
        """将项目详情转换为Markdown格式的报告"""
        if not project_details:
            return "# 项目详情报告\n\n项目信息未找到。"

        project_info = project_details['project_info']

        markdown = f"""# 项目详情报告: {project_info['name']}

## 项目基本信息

**项目名称**: {project_info['name']}
**项目描述**: {project_info['description']}
**项目类型**: {project_info['project_type']}
**项目状态**: {project_info['status']}
**项目进度**: {project_info['progress']}% (计算进度: {project_info['calculated_progress']}%)
**项目标签**: {', '.join(project_info['tags']) if project_info['tags'] else '无'}
**是否公开**: {'是' if project_info['is_public'] else '否'}
**总投资额**: ¥{project_info['total_investment']:,.2f}
**项目估值**: ¥{project_info['valuation']:,.2f}
**融资轮次**: {project_info['funding_rounds']}轮
**成员数量**: {project_info['member_count']}人
**开始时间**: {project_info['start_date'] or '未设定'}
**结束时间**: {project_info['end_date'] or '未设定'}
**创建时间**: {project_info['created_at'][:10]}
**最后更新**: {project_info['updated_at'][:10]}
**项目负责人**: {project_info['owner']['username']} ({project_info['owner']['first_name']} {project_info['owner']['last_name']})

## 项目成员信息

**总成员数**: {len(project_details['members'])}人

"""

        # 添加成员详情
        if project_details['members']:
            markdown += "### 成员列表\n\n"
            for i, member in enumerate(project_details['members'], 1):
                markdown += f"""**成员 {i}**: {member['username']} ({member['first_name']} {member['last_name']})
- 角色: {member['role']}
- 贡献比例: {member['contribution_percentage']}%
- 股份比例: {member['equity_percentage']}%
- 投资金额: ¥{member['investment_amount']:,.2f}
- 加入时间: {member['join_date'][:10]}
- 贡献描述: {member['contribution_description'] or '无'}

"""

        # 添加任务信息
        tasks_info = project_details['tasks']
        markdown += f"""## 项目任务信息

**总任务数**: {tasks_info['total_count']}个

### 任务状态分布
"""
        for status, count in tasks_info['status_summary'].items():
            markdown += f"- {status}: {count}个\n"

        if tasks_info['tasks']:
            markdown += "\n### 任务详情\n\n"
            for i, task in enumerate(tasks_info['tasks'], 1):
                assignee_info = f"{task['assignee']['username']} ({task['assignee']['name']})" if task['assignee'] else '未分配'
                markdown += f"""**任务 {i}**: {task['title']}
- 描述: {task['description'] or '无'}
- 状态: {task['status']}
- 优先级: {task['priority']}
- 进度: {task['progress']}%
- 创建者: {task['creator']['username']} ({task['creator']['name']})
- 负责人: {assignee_info}
- 预估工时: {task['estimated_hours'] or '未设定'}小时
- 开始日期: {task['start_date'] or '未设定'}
- 截止日期: {task['due_date'][:10] if task['due_date'] else '未设定'}
- 是否公开: {'是' if task['is_public'] else '否'}
- 创建时间: {task['created_at'][:10]}

"""

        # 添加收益信息
        revenue_info = project_details['revenue']
        markdown += f"""## 项目收益信息

**总收益**: ¥{revenue_info['total_revenue']:,.2f}
**净收益**: ¥{revenue_info['total_net_revenue']:,.2f}
**收益记录数**: {revenue_info['revenue_count']}条

"""

        if revenue_info['revenues']:
            markdown += "### 收益详情\n\n"
            for i, revenue in enumerate(revenue_info['revenues'], 1):
                markdown += f"""**收益 {i}**: {revenue['revenue_type']}
- 金额: ¥{revenue['amount']:,.2f}
- 净金额: ¥{revenue['net_amount']:,.2f}
- 相关成本: ¥{revenue['associated_costs']:,.2f}
- 描述: {revenue['description']}
- 来源: {revenue['source'] or '未填写'}
- 收益日期: {revenue['revenue_date']}
- 是否已分配: {'是' if revenue['is_distributed'] else '否'}
- 记录人: {revenue['recorded_by']}

"""

        # 添加招募信息
        recruitment_info = project_details['recruitment']
        if recruitment_info['recruitment_count'] > 0:
            markdown += f"""## 项目招募信息

**招募岗位数**: {recruitment_info['recruitment_count']}个

### 招募详情

"""
            for i, recruitment in enumerate(recruitment_info['recruitments'], 1):
                markdown += f"""**招募 {i}**: {recruitment['title']}
- 描述: {recruitment['description']}
- 所需技能: {', '.join(recruitment['required_skills']) if recruitment['required_skills'] else '无'}
- 技能等级: {recruitment['skill_level_required']}
- 工作类型: {recruitment['work_type']}
- 需要人数: {recruitment['positions_needed']}人
- 已招募: {recruitment['positions_filled']}人
- 预期投入: {recruitment['expected_commitment'] or '未填写'}
- 薪资范围: {recruitment['salary_range'] or '未填写'}
- 股份范围: {recruitment['equity_percentage_min']}% - {recruitment['equity_percentage_max']}%
- 状态: {recruitment['status']}
- 申请人数: {recruitment['application_count']}人
- 发布时间: {recruitment['created_at'][:10]}

"""

        # 添加功分信息
        merit_info = project_details['merit']
        if merit_info['merit_records_count'] > 0:
            markdown += f"""## 项目功分信息

**总功分**: {merit_info['total_merit_points']:.2f}分
**功分记录数**: {merit_info['merit_records_count']}条

### 功分详情

"""
            for i, merit in enumerate(merit_info['merits'], 1):
                markdown += f"""**功分记录 {i}**:
- 用户: {merit['user']}
- 分数: {merit['points']:.2f}分
- 原因: {merit['reason']}
- 颁发者: {merit['awarded_by'] or '系统'}
- 时间: {merit['created_at'][:10]}

"""

        # 添加最近活动日志
        logs_info = project_details['logs']
        if logs_info['recent_logs_count'] > 0:
            markdown += f"""## 最近项目活动

**最近活动记录数**: {logs_info['recent_logs_count']}条

### 活动详情

"""
            for i, log in enumerate(logs_info['logs'][:20], 1):  # 只显示前20条
                markdown += f"""**活动 {i}**: {log['title']}
- 类型: {log['log_type']}
- 操作用户: {log['user']}
- 描述: {log['description'] or '无'}
- 时间: {log['created_at'][:19]}

"""

        # 添加生成信息
        markdown += f"""

---

**报告生成时间**: {project_details['generated_at'][:19]}
**数据来源**: 项目管理系统数据库
**报告用途**: AI分析基础数据

"""

        return markdown