from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.voting.models import VotingRound


class Command(BaseCommand):
    help = '创建和管理投票轮次'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create',
            action='store_true',
            help='创建新的投票轮次',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='列出所有投票轮次',
        )
        parser.add_argument(
            '--activate',
            type=int,
            help='激活指定ID的投票轮次',
        )
        parser.add_argument(
            '--deactivate',
            type=int,
            help='停用指定ID的投票轮次',
        )
        parser.add_argument(
            '--name',
            type=str,
            help='投票轮次名称',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='投票轮次持续天数（默认7天）',
        )

    def handle(self, *args, **options):
        if options['create']:
            self.create_voting_round(options)
        elif options['list']:
            self.list_voting_rounds()
        elif options['activate']:
            self.activate_round(options['activate'])
        elif options['deactivate']:
            self.deactivate_round(options['deactivate'])
        else:
            self.stdout.write('请指定操作参数，使用 --help 查看帮助')

    def create_voting_round(self, options):
        # 先停用所有活跃轮次
        VotingRound.objects.filter(is_active=True).update(is_active=False)
        
        name = options.get('name') or f"投票轮次-{timezone.now().strftime('%Y%m%d')}"
        days = options.get('days', 7)
        
        round_data = {
            'name': name,
            'description': f'投融资投票轮次，持续{days}天',
            'start_time': timezone.now(),
            'end_time': timezone.now() + timedelta(days=days),
            'is_active': True,
            'is_self_evaluation_open': False,
            'max_self_investment': 10.00
        }
        
        new_round = VotingRound.objects.create(**round_data)
        self.stdout.write(
            self.style.SUCCESS(f'成功创建投票轮次: {new_round.name} (ID: {new_round.id})')
        )

    def list_voting_rounds(self):
        rounds = VotingRound.objects.all().order_by('-created_at')
        if not rounds:
            self.stdout.write('没有找到任何投票轮次')
            return
            
        self.stdout.write('所有投票轮次:')
        for round in rounds:
            status = '🟢 活跃' if round.is_active else '🔴 停用'
            self_eval = '🟢 开放' if round.is_self_evaluation_open else '🔴 关闭'
            self.stdout.write(
                f'ID: {round.id} | {round.name} | {status} | 自评: {self_eval} | 创建: {round.created_at.strftime("%Y-%m-%d %H:%M")}'
            )

    def activate_round(self, round_id):
        try:
            # 先停用所有活跃轮次
            VotingRound.objects.filter(is_active=True).update(is_active=False)
            
            # 激活指定轮次
            round = VotingRound.objects.get(id=round_id)
            round.is_active = True
            round.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'成功激活投票轮次: {round.name}')
            )
        except VotingRound.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'投票轮次 ID {round_id} 不存在')
            )

    def deactivate_round(self, round_id):
        try:
            round = VotingRound.objects.get(id=round_id)
            round.is_active = False
            round.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'成功停用投票轮次: {round.name}')
            )
        except VotingRound.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'投票轮次 ID {round_id} 不存在')
            )