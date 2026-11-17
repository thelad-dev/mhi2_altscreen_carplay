/* Host test: display-size-aware ViewArea/SafeArea defaults of the GEN2 adapter.
 * Covers the unchanged 1010x376 reference and the 800x480 candidate geometry.
 * No target hooks, no sockets, no vehicle behavior is exercised.
 * Usage: test_gen2_geometry PATH/TO/vw-mu1367.conf */
#define ALT111_GEN2_HOST_TEST 1
static char recovery_path[192];
#define ALT111_RECOVERY_PATH recovery_path
static char safe_path_fmt[160],platform_defaults_path[160];
#define MIBR_GEN2_SAFE_PATH_FMT safe_path_fmt
#define MIBR_GEN2_PLATFORM_DEFAULTS platform_defaults_path
#include "../libaltscreen111_gen2.c"
#include <assert.h>

static void write_file(const char *path,const char *text)
{
    FILE *f=fopen(path,"w");
    assert(f);
    assert(fputs(text,f)>=0);
    assert(!fclose(f));
}

static void copy_file(const char *from,const char *to)
{
    char buf[2048];
    size_t n;
    FILE *in=fopen(from,"r"),*out=fopen(to,"w");
    assert(in&&out);
    n=fread(buf,1,sizeof(buf)-1,in);
    buf[n]=0;
    assert(n>0&&fputs(buf,out)>=0);
    fclose(in);fclose(out);
}

/* Load display + areas under a fresh registry snapshot. stored_key, when set,
 * is stored in the persistent layer with the given value. */
static void load_all(const char *stored_key,const char *stored_value,
                     struct mibr_display_config *display,
                     struct mibr_viewareas_config *views)
{
    struct gen2_settings_scope scope;
    struct alt111_settings desired;
    assert(!alt111_settings_defaults(&desired,"mibr_dual_view"));
    assert(!alt111_settings_set(&desired,ALTSET_VIEWAREAS_COUNT,"3",ALT111_TEMP));
    if(stored_key)
        assert(!alt111_settings_set(&desired,alt111_setting_find(stored_key),stored_value,ALT111_PERSISTENT));
    memset(&scope,0,sizeof(scope));scope.settings=desired;scope.valid=1;
    assert(!pthread_setspecific(g_settings_scope_key,&scope));
    load_display_config(display);
    load_viewareas_config(views);
    assert(!pthread_setspecific(g_settings_scope_key,NULL));
}

static void expect_safe(const struct mibr_viewareas_config *v,int i,int x,int y,int w,int h)
{
    assert(v->view[i].safe_x==x&&v->view[i].safe_y==y&&v->view[i].safe_w==w&&v->view[i].safe_h==h);
}

static void expect_outer(const struct mibr_viewareas_config *v,int w,int h)
{
    int i;
    for(i=0;i<(int)v->count;++i)
        assert(v->view[i].x==0&&v->view[i].y==0&&v->view[i].w==w&&v->view[i].h==h);
}

static int inside(const struct alt111_geom_rect *a,const struct alt111_geom_rect *b)
{
    return a->x>=b->x&&a->y>=b->y&&a->x+a->w<=b->x+b->w&&a->y+a->h<=b->y+b->h;
}

static void test_table(void)
{
    const struct alt111_geom_preset *p;
    unsigned i;
    int k;
    assert(alt111_geom_find(1010,376)&&alt111_geom_find(800,480));
    assert(!alt111_geom_find(1000,500)&&!alt111_geom_find(480,800));
    p=alt111_geom_find(1010,376);
    /* reference values must not move (previously hard-wired in viewareas_defaults) */
    assert(p->safe[1].x==0&&p->safe[1].y==58&&p->safe[1].w==1010&&p->safe[1].h==248);
    assert(p->safe[2].x==370&&p->safe[2].y==58&&p->safe[2].w==256&&p->safe[2].h==248);
    for(i=0;i<sizeof(alt111_geom_presets)/sizeof(alt111_geom_presets[0]);++i){
        struct alt111_geom_rect canvas;
        p=&alt111_geom_presets[i];
        canvas.x=0;canvas.y=0;canvas.w=p->width;canvas.h=p->height;
        assert(inside(&p->safe[0],&canvas)&&inside(&p->safe[1],&p->safe[0])&&inside(&p->safe[2],&p->safe[1]));
        for(k=0;k<3;++k)assert(p->safe[k].w>=100&&p->safe[k].h>=60);
    }
    /* 800x480 derivation rules: 16 px macroblock grid, bands >= measured 58/70 px, center 256 wide centered */
    p=alt111_geom_find(800,480);
    for(k=0;k<3;++k)
        assert(p->safe[k].x%16==0&&p->safe[k].y%16==0&&p->safe[k].w%16==0&&p->safe[k].h%16==0);
    assert(p->safe[1].y>=58&&480-(p->safe[1].y+p->safe[1].h)>=70);
    assert(p->safe[2].w==256&&p->safe[2].x*2+p->safe[2].w==800);
}

int main(int argc,char **argv)
{
    char root[]="/tmp/alt111-gen2-geom-XXXXXX",broker[192];
    struct mibr_display_config display;
    struct mibr_viewareas_config views;
    assert(argc==2);
    assert(mkdtemp(root));
    (void)settings_scope(); /* creates g_settings_scope_key */
    snprintf(safe_path_fmt,sizeof(safe_path_fmt),"%s/%%s.conf",root);
    snprintf(platform_defaults_path,sizeof(platform_defaults_path),"%s/plat.conf",root);
    snprintf(broker,sizeof(broker),"%s/safe-voll.conf",root);
    unsetenv("ALTSCREEN111_WIDTH");unsetenv("ALTSCREEN111_HEIGHT");
    unsetenv("ALTSCREEN111_WIDTH_MM");unsetenv("ALTSCREEN111_HEIGHT_MM");

    test_table();

    /* 1010x376 reference: nothing changes. */
    load_display_config(&display); /* no snapshot: compiled defaults */
    assert(display.width==1010&&display.height==376&&display.width_mm==200&&display.height_mm==74);
    load_all(NULL,NULL,&display,&views); /* registry profile defaults of mibr_dual_view */
    assert(display.width==1010&&display.height==376&&display.width_mm==202&&display.height_mm==75);
    expect_outer(&views,1010,376);
    viewareas_defaults(&views);
    expect_outer(&views,1010,376);
    expect_safe(&views,0,0,0,1010,376);
    expect_safe(&views,1,0,58,1010,248);
    expect_safe(&views,2,370,58,256,248);
    assert(views.view[0].adjacent==1&&views.view[1].adjacent==0&&views.view[2].adjacent==0);

    /* 800x480 from the profile-bound environment (registry snapshot present, only profile layer). */
    setenv("ALTSCREEN111_WIDTH","800",1);setenv("ALTSCREEN111_HEIGHT","480",1);
    load_all(NULL,NULL,&display,&views);
    assert(display.width==800&&display.height==480&&display.width_mm==200&&display.height_mm==120);
    assert(views.count==3);
    expect_outer(&views,800,480);
    expect_safe(&views,0,0,0,800,480);
    expect_safe(&views,1,0,64,800,336);
    expect_safe(&views,2,272,64,256,336);

    /* The shipped platform defaults file gives the same rectangles (no drift between table and file). */
    copy_file(argv[1],platform_defaults_path);
    load_all(NULL,NULL,&display,&views);
    expect_safe(&views,0,0,0,800,480);
    expect_safe(&views,1,0,64,800,336);
    expect_safe(&views,2,272,64,256,336);

    /* A menu choice beats the platform default; a stored registry value beats it too. */
    write_file(broker,"revision=1\nvalue=16,48,768,368\n");
    load_all(NULL,NULL,&display,&views);
    expect_safe(&views,1,16,48,768,368);
    unlink(broker);
    load_all("viewarea.1.safe.y","32",&display,&views);
    assert(views.view[1].safe_y==32);
    unlink(platform_defaults_path);

    /* A platform default outside the 800x480 area is rejected: the compiled preset stays. */
    write_file(platform_defaults_path,"safe_voll=0,0,1010,376\n");
    load_all(NULL,NULL,&display,&views);
    expect_safe(&views,1,0,64,800,336);
    unlink(platform_defaults_path);

    /* A size without a preset row: full canvas for all areas, physical height from the ratio. */
    setenv("ALTSCREEN111_WIDTH","1000",1);setenv("ALTSCREEN111_HEIGHT","500",1);
    load_all(NULL,NULL,&display,&views);
    assert(display.width==1000&&display.height==500&&display.height_mm==100);
    expect_outer(&views,1000,500);
    expect_safe(&views,1,0,0,1000,500);
    expect_safe(&views,2,0,0,1000,500);

    /* An explicit physical height is honored for any size. */
    setenv("ALTSCREEN111_WIDTH","800",1);setenv("ALTSCREEN111_HEIGHT","480",1);
    setenv("ALTSCREEN111_HEIGHT_MM","110",1);
    load_all(NULL,NULL,&display,&views);
    assert(display.height_mm==110);

    puts("GEN2_GEOMETRY_TEST=PASS");
    return 0;
}
