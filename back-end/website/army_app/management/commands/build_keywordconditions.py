import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from army_app.models import AbilityEffect, Enhancement, Stratagem

class Command(BaseCommand):
    help = "Build/Rebuild KeyWordCondition trees from keyword_expression"
    
    def add_arguments(self, parser):
        parser.add_argument( "--model", type=str, help="Choose specific model to build", required=False)
        
        parser.add_argument("--id", type=int, help="Process a single object by id", required=False)
        
        parser.add_argument("--dry-run", type=str, help="Parse the expression without saving", required=False)
        
    def handle(self, *args, **options):
        model_name = options.get("model")
        obj_id = options.get("id")
        dry_run = options.get("dry-run")
        
        model_map = {
            "Ability Effect" : AbilityEffect,
            "Stratagem" : Stratagem,
            "Enhancement" : Enhancement,
        }
        
        models_to_process = []
        if model_name:
            if model_name not in model_map:
                self.stderr.write(f"Unknown model : {model_name}")
                return
            models_to_process = [model_map[model_name]]
        else:
            # All models processed by default
            models_to_process = list(model_map.values())
        
        # Total Stats
        total_processed = 0
        total_success = 0
        total_failed = 0
        
        for model in models_to_process:
            queryset = model.objects.all()
            if obj_id:
                queryset = queryset.filter(id=obj_id)
                
            count = queryset.count()
            self.stdout.write(f"Processing {count} objects for model {model.__name__}...")
            
            # Model Stats
            success = 0
            fails = 0
        
            for obj in queryset:
                expr = getattr(obj, "keyword_express", None)
                if not expr:
                    self.stderr.write(f"Object has no keyword expression attribute")
                    continue
                
                try:
                    with transaction.atomic():
                        # Delete old tree
                        if not dry_run and getattr(obj, "auto_condition", None):
                            obj.auto_condition.delete()
                        
                        # Parse expression and build tree here (not built yet)
                        condition - parse_expression(expr)
                        
                        if not dry_run:
                            obj.auto_condition = condition
                            obj.save()
                        
                        success += 1
                        self.stdout.write(f"[OK] - {obj.id}: parsed")
                
                except Exception as e:
                    fails += 1
                    self.stderr.write(f"[FAIL] - {obj.id}: {e}")
                    
                self.stdout.write(f"[INFO] = model {model.__name__} has parsed {success} objs and failed to parse {fails} objs...")
            
            total_processed += count
            total_failed += fails
            total_success += success
            
        # Summary
        self.stdout.write("\n--- Summary ---")
        self.stdout.write(f"Total objects processed: {total_processed}")
        self.stdout.write(f"Success: {total_success}")
        self.stdout.write(f"Failed: {total_failed}")
        return super().handle(*args, **options)