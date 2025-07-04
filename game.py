import random

WIDTH = 800 
HEIGHT = 600
TITLE = "Platformer Game - João Carneiro"

PLAYER_SPEED = 5
GRAVITY = 1
JUMP_FORCE = -22
PARALLAX_FACTOR = 0.2


camera_offset_x = 0
camera_offset_y = 0
score = 0
total_coins_in_level = 0
total_enemies_in_level = 0 
coins = []
game_state = 'menu'
menu_message = "My Platformer Game"
sound_enabled = True


center_x = WIDTH / 2
start_button = Actor('botao_iniciar', pos=(center_x, 250))
audio_button = Actor('botao_audio_on', pos=(center_x, 350))
exit_button = Actor('botao_sair', pos=(center_x, 450))


class AnimationManager:
    """ Manages animation frames and timers for any object. """
    def __init__(self, sprite_prefix):
        self.animations = {
            'idle': [f'{sprite_prefix}_idle_0', f'{sprite_prefix}_idle_1'],
            'walk_right': [f'{sprite_prefix}_walk_0', f'{sprite_prefix}_walk_1'],
            'walk_left': [f'{sprite_prefix}_walk_left_0', f'{sprite_prefix}_walk_left_1'],
            'spin': [f'{sprite_prefix}_0', f'{sprite_prefix}_1']
        }
        self.current_frame = 0
        self.animation_timer = 0
        self.speeds = {'idle': 20, 'walk': 5, 'spin': 8}

    def update(self, state, direction='right'):
        current_anim_speed = self.speeds.get(state, 10)
        self.animation_timer += 1
        if self.animation_timer > current_anim_speed:
            self.animation_timer = 0
            self.current_frame += 1
        
        anim_key = 'walk_right' if state == 'walk' and direction == 'right' else \
                   'walk_left' if state == 'walk' and direction == 'left' else state
        
        if anim_key in self.animations and self.animations[anim_key]:
            current_anim = self.animations[anim_key]
            if self.current_frame >= len(current_anim):
                self.current_frame = 0
            return current_anim[self.current_frame]
        return f'{sprite_prefix}_idle_0'

class Character:
    """ Template for player and enemies, with physics and animation delegation. """
    def __init__(self, sprite_prefix, pos, speed, active=True, type='player'):
        self.anim_manager = AnimationManager(sprite_prefix)
        self.actor = Actor(self.anim_manager.update('idle'), pos=pos)
        self.hitbox = self.actor.copy()
        self.hitbox.inflate_ip(-20, -10)
        self.hitbox_offset_y = 5
        self.speed = speed
        self.velocity_x = 0
        self.velocity_y = 0
        self.can_jump = False
        self.active = active
        self.state = 'idle'
        self.direction = 'right'
        self.patrol_direction = 1
        self.type = type

    def draw(self, offset_x, offset_y):
        draw_pos = (self.actor.left - offset_x, self.actor.top - offset_y)
        screen.blit(self.actor._surf, draw_pos)

    def jump(self):
        if self.can_jump:
            self.velocity_y = JUMP_FORCE
            self.can_jump = False
            if sound_enabled and hasattr(sounds, 'player_jump'):
                sounds.player_jump.play()

    def die(self):
        if not sound_enabled: return
        if self.type == 'enemy' and hasattr(sounds, 'enemy_stomp'):
            sounds.enemy_stomp.play()
        elif self.type == 'player' and hasattr(sounds, 'player_hurt'):
            sounds.player_hurt.play()

    def update(self, platforms, world_bounds):
        world_start_x, world_end_x = world_bounds
        if self.active: self.hitbox.x += self.velocity_x
        if self.hitbox.left < world_start_x:
            self.hitbox.left = world_start_x
            if self.type == 'enemy': self.patrol_direction = 1
        elif self.hitbox.right > world_end_x:
            self.hitbox.right = world_end_x
            if self.type == 'enemy': self.patrol_direction = -1
        for platform in platforms:
            if self.hitbox.colliderect(platform):
                if self.velocity_x > 0 and abs(self.hitbox.right - platform.left) < self.speed + 1:
                    self.hitbox.right = platform.left
                    if self.active and self.type == 'enemy':
                        self.patrol_direction *= -1
                        self.velocity_x = 0
                elif self.velocity_x < 0 and abs(self.hitbox.left - platform.right) < self.speed + 1:
                    self.hitbox.left = platform.right
                    if self.active and self.type == 'enemy':
                        self.patrol_direction *= -1
                        self.velocity_x = 0
        self.velocity_y += GRAVITY
        self.hitbox.y += self.velocity_y
        self.can_jump = False
        for platform in platforms:
            if self.hitbox.colliderect(platform):
                if self.velocity_y > 0 and self.hitbox.bottom <= platform.top + self.velocity_y:
                    self.hitbox.bottom = platform.top
                    self.velocity_y = 0
                    self.can_jump = True
                elif self.velocity_y < 0 and self.hitbox.top >= platform.bottom - abs(self.velocity_y):
                    self.hitbox.top = platform.bottom
                    self.velocity_y = 0
        self.actor.centerx = self.hitbox.centerx
        self.actor.centery = self.hitbox.centery - self.hitbox_offset_y
        if self.velocity_x == 0: self.state = 'idle'
        else:
            self.state = 'walk'
            self.direction = 'right' if self.velocity_x > 0 else 'left'
        new_image = self.anim_manager.update(self.state, self.direction)
        self.actor.image = new_image

class Coin:
    """ Class for "Coin" object that is animated """
    def __init__(self, pos):
        self.anim_manager = AnimationManager('coin')
        self.actor = Actor(self.anim_manager.update('spin'), pos=pos)
    def draw(self, offset_x, offset_y):
        draw_pos = (self.actor.left - offset_x, self.actor.top - offset_y)
        screen.blit(self.actor._surf, draw_pos)
    def update(self):
        new_image = self.anim_manager.update('spin')
        self.actor.image = new_image


player = Character(sprite_prefix='player', pos=(WIDTH / 2, 0), speed=PLAYER_SPEED, active=True, type='player')
platforms = []
enemies = []
ground_start_x = 0
ground_end_x = 0

def generate_level():
    global platforms, enemies, coins, ground_start_x, ground_end_x, total_coins_in_level, total_enemies_in_level
    platforms.clear(); enemies.clear(); coins.clear()
    total_coins_in_level = 0
    total_enemies_in_level = 0 
    
    ground_middle_sprite = 'terrain_sand_block_top'
    ground_block_width = Actor(ground_middle_sprite).width
    num_ground_platforms = (WIDTH * 4) // ground_block_width 
    for i in range(num_ground_platforms):
        pos_x = i * ground_block_width - (WIDTH * 1.5) 
        pos_y = HEIGHT - 20
        ground_platform = Actor(ground_middle_sprite, (pos_x, pos_y))
        platforms.append(ground_platform)
    
    ground_start_x = platforms[0].left
    ground_end_x = platforms[-1].right

    
    safe_zone_radius = WIDTH / 2     
    num_clusters = 30
    horizontal_padding = 1.8 * player.actor.width
    vertical_padding = 2 * player.actor.height
    brick_platform_width = Actor('bricks_brown').width
    brick_platform_height = Actor('bricks_brown').height
    generated_cluster_rects = []

    for _ in range(num_clusters):
        attempts = 0
        while attempts < 100:
            platforms_in_cluster = random.randint(1, 5)
            total_cluster_width = platforms_in_cluster * brick_platform_width
            candidate_x_start = random.uniform(ground_start_x, ground_end_x - total_cluster_width)
            candidate_y_center = (HEIGHT - 20) - random.uniform(player.actor.height * 1.5, player.actor.height * 4)
            if candidate_y_center < 100:
                candidate_y_center = 100

            candidate_rect = Rect((candidate_x_start, candidate_y_center - brick_platform_height / 2), (total_cluster_width, brick_platform_height))
            candidate_rect_with_padding = candidate_rect.inflate(horizontal_padding, vertical_padding)
            is_position_valid = True
            for existing_rect in generated_cluster_rects:
                if candidate_rect_with_padding.colliderect(existing_rect):
                    is_position_valid = False
                    break 
            if is_position_valid:
                break 
            attempts += 1
        
        if attempts < 100:
            platforms_in_this_cluster = []
            for i in range(platforms_in_cluster):
                pos_x = candidate_rect.left + (brick_platform_width / 2) + (i * brick_platform_width)
                platform = Actor('bricks_brown', pos=(pos_x, candidate_rect.centery))
                platforms.append(platform)
                platforms_in_this_cluster.append(platform)
            
            generated_cluster_rects.append(candidate_rect)
            if random.random() < 0.8 and platforms_in_this_cluster:
                chosen_platform = random.choice(platforms_in_this_cluster)
                distance_from_start = abs(chosen_platform.x - player.actor.x)*1.5
                if distance_from_start > safe_zone_radius:
                    enemy = Character(sprite_prefix='zombie', pos=(chosen_platform.x, chosen_platform.top - 20), speed=2, active=False, type='enemy')
                    enemies.append(enemy)
                    total_enemies_in_level += 1 

            for p in platforms_in_this_cluster:
                if random.random() < 0.5:
                    coin = Coin(pos=(p.x, p.top - 20))
                    coins.append(coin)
                    total_coins_in_level += 1

def reset_game():
    """ Resets the player state and generates a new level. """
    global score, menu_message
    score = 0
    menu_message = "My Platformer Game"
    player.actor.pos = (WIDTH / 4, 0)
    player.actor.top = 0 
    player.velocity_x = 0
    player.velocity_y = 0
    player.can_jump = False
    player.hitbox.center = player.actor.center
    
    generate_level()
    
    if sound_enabled:
        music.play('environment_song.wav')

def on_music_end():
    if sound_enabled and game_state == 'playing': music.play('environment_song.wav')

def draw_menu():
    screen.fill((135, 206, 235)); screen.draw.text(menu_message, center=(WIDTH / 2, 100), fontsize=60, color="white", owidth=1.5, ocolor="black")
    start_button.draw(); audio_button.draw(); exit_button.draw()

def draw_game():
    global camera_offset_x, camera_offset_y
    screen.fill((243, 199, 165))
    background_width = Actor('background_color_desert').width
    parallax_offset_x = camera_offset_x * PARALLAX_FACTOR
    num_visible_tiles = (WIDTH / background_width) + 2; start_tile_index = int(parallax_offset_x // background_width)
    for i in range(int(num_visible_tiles)):
        pos_x = (start_tile_index + i) * background_width - parallax_offset_x; screen.blit('background_color_desert', (pos_x, 0))
    for platform in platforms:
        if platform.right > camera_offset_x and platform.left < camera_offset_x + WIDTH:
             draw_pos = (platform.left - camera_offset_x, platform.top - camera_offset_y); screen.blit(platform._surf, draw_pos)
    for coin in coins:
        if coin.actor.right > camera_offset_x and coin.actor.left < camera_offset_x + WIDTH: coin.draw(camera_offset_x, camera_offset_y)
    player.draw(camera_offset_x, camera_offset_y)
    for enemy in enemies: enemy.draw(camera_offset_x, camera_offset_y)
    screen.draw.text(f"Score: {score}", topright=(WIDTH - 20, 10), fontsize=40, color="white", owidth=1, ocolor="black")

def update_game():
    global camera_offset_x, camera_offset_y, score, game_state, menu_message
    player.velocity_x = 0
    if keyboard.left: player.velocity_x = -player.speed
    elif keyboard.right: player.velocity_x = player.speed
    if keyboard.space: player.jump()
    for enemy in enemies:
        if not enemy.active and enemy.actor.right < camera_offset_x + WIDTH + 50: 
            enemy.active = True
        if enemy.active: enemy.velocity_x = enemy.speed * enemy.patrol_direction
        else: enemy.velocity_x = 0

    bounds = (ground_start_x, ground_end_x)
    player.update(platforms, bounds)
    for enemy in enemies:
        enemy.update(platforms, bounds)
    for coin in coins:
        coin.update()
            
    ideal_offset_x = player.actor.centerx - WIDTH / 2
    camera_offset_x = max(ground_start_x, min(ideal_offset_x, ground_end_x - WIDTH))
    
    for coin in coins[:]:
        if player.hitbox.colliderect(coin.actor):
            coins.remove(coin) 
            score += 1
            if sound_enabled and hasattr(sounds, 'collect_coin'):
                sounds.collect_coin.play()
                
    enemies_stomped = []
    player_is_hurt = False

    for enemy in enemies:
        if player.hitbox.colliderect(enemy.hitbox):
            if player.velocity_y > 0 and player.hitbox.bottom < enemy.hitbox.centery + 10:
                enemies_stomped.append(enemy)
            else:
                if player.velocity_x != 0 or enemy.velocity_x != 0:
                    player_is_hurt = True

    if enemies_stomped:# Play music if enabled
    if total_coins_in_level > 0 and len(coins) == 0:
        level_won = True
    elif total_enemies_in_level > 0 and len(enemies) == 0:
        level_won = True        
    if level_won:
        music.stop()
        game_state = 'menu'
        menu_message = "You Won!"

def on_mouse_down(pos):
    global game_state, sound_enabled
    if game_state == 'menu':
        if start_button.collidepoint(pos): game_state = 'playing'; reset_game()
        elif audio_button.collidepoint(pos):
            sound_enabled = not sound_enabled
            if sound_enabled: audio_button.image = 'botao_audio_on'; music.unpause()
            else: audio_button.image = 'botao_audio_off'; music.pause()
        elif exit_button.collidepoint(pos): quit()

def draw():
    if game_state == 'menu': draw_menu()
    elif game_state == 'playing': draw_game()

def update():
    if game_state == 'playing': update_game()