import asyncio
from pathlib import Path

from conf import BASE_DIR
from uploader.douyin_uploader.main import DouYinVideo
from uploader.ks_uploader.main import KSVideo
from uploader.tencent_uploader.main import TencentVideo
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo
from uploader.bilibili_uploader.main import BilibiliUploader, random_emoji
from uploader.baijiahao_uploader.main import BaiJiaHaoVideo
from utils.constant import TencentZoneTypes, VideoZoneTypes
from utils.files_times import generate_schedule_time_next_day


def post_video_tencent(
    title,
    files,
    tags,
    account_file,
    category=TencentZoneTypes.LIFESTYLE.value,
    enableTimer=False,
    videos_per_day=1,
    daily_times=None,
    start_days=0,
    is_draft=False,
    description="",
    thumbnail_path="",
):
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(
            len(files), videos_per_day, daily_times, start_days
        )
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            try:
                app = TencentVideo(
                    title,
                    str(file),
                    tags,
                    publish_datetimes[index],
                    cookie,
                    category,
                    is_draft,
                    description,
                    thumbnail_path,
                )
                asyncio.run(app.main(), debug=False)
            except Exception as e:
                print(f"视频号上传失败: {str(e)}")
                import traceback

                traceback.print_exc()


def post_video_DouYin(
    title,
    files,
    tags,
    account_file,
    category=TencentZoneTypes.LIFESTYLE.value,
    enableTimer=False,
    videos_per_day=1,
    daily_times=None,
    start_days=0,
    thumbnail_path="",
    productLink="",
    productTitle="",
    description="",
):
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(
            len(files), videos_per_day, daily_times, start_days
        )
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            try:
                app = DouYinVideo(
                    title,
                    str(file),
                    tags,
                    publish_datetimes[index],
                    cookie,
                    thumbnail_path,
                    productLink,
                    productTitle,
                    description,
                )
                asyncio.run(app.main(), debug=False)
            except Exception as e:
                print(f"抖音上传失败: {str(e)}")
                import traceback

                traceback.print_exc()


def post_video_ks(
    title,
    files,
    tags,
    account_file,
    category=TencentZoneTypes.LIFESTYLE.value,
    enableTimer=False,
    videos_per_day=1,
    daily_times=None,
    start_days=0,
    description="",
    thumbnail_path="",
):
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(
            len(files), videos_per_day, daily_times, start_days
        )
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            try:
                app = KSVideo(
                    title,
                    str(file),
                    tags,
                    publish_datetimes[index],
                    cookie,
                    description,
                    thumbnail_path,
                )
                asyncio.run(app.main(), debug=False)
            except Exception as e:
                print(f"快手上传失败: {str(e)}")
                import traceback

                traceback.print_exc()


def post_video_xhs(
    title,
    files,
    tags,
    account_file,
    category=TencentZoneTypes.LIFESTYLE.value,
    enableTimer=False,
    videos_per_day=1,
    daily_times=None,
    start_days=0,
    description="",
    thumbnail_path="",
):
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    file_num = len(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(
            file_num, videos_per_day, daily_times, start_days
        )
    else:
        publish_datetimes = 0
    for index, file in enumerate(files):
        for cookie in account_file:
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            try:
                app = XiaoHongShuVideo(
                    title,
                    file,
                    tags,
                    publish_datetimes,
                    cookie,
                    thumbnail_path,
                    description,
                )
                asyncio.run(app.main(), debug=False)
            except Exception as e:
                print(f"小红书上传失败: {str(e)}")
                import traceback

                traceback.print_exc()


def post_video_bilibili(
    title,
    files,
    tags,
    account_file,
    category=VideoZoneTypes.LIFE.value,
    enableTimer=False,
    videos_per_day=1,
    daily_times=None,
    start_days=0,
    description="",
    thumbnail_path="",
):
    """
    Bilibili视频发布函数 - 使用Playwright模拟浏览器操作

    参数:
        title: 视频标题
        files: 视频文件列表
        tags: 标签列表
        account_file: 账号cookie文件列表
        category: 视频分区ID，默认为生活分区
        enableTimer: 是否启用定时发布
        videos_per_day: 每天发布视频数
        daily_times: 每天发布时间点列表
        start_days: 开始天数
        description: 视频简介

    返回:
        dict: {"success": bool, "failed_files": list}
    """
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]

    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(
            len(files), videos_per_day, daily_times, start_days
        )
    else:
        publish_datetimes = [0 for _ in range(len(files))]

    failed_files = []
    success_count = 0

    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")

            try:
                # 添加随机emoji避免标题重复
                video_title = title + random_emoji()

                # 视频简介，如果没有则使用标题
                desc = description if description else video_title

                # 创建上传器实例
                bili_uploader = BilibiliUploader(
                    title=video_title,
                    file_path=str(file),
                    tags=tags,
                    publish_date=publish_datetimes[index],
                    account_file=str(cookie),
                    tid=category,  # 分区ID
                    description=desc,
                    thumbnail_path=thumbnail_path,
                )

                # 执行上传
                result = asyncio.run(bili_uploader.main())
                if result:
                    print(f"✅ {file.name} 上传成功")
                    success_count += 1
                else:
                    print(f"❌ {file.name} 上传失败")
                    failed_files.append(str(file.name))

            except Exception as e:
                print(f"❌ 上传视频 {file.name} 时出错: {str(e)}")
                failed_files.append(str(file.name))

    return {
        "success": len(failed_files) == 0,
        "success_count": success_count,
        "failed_count": len(failed_files),
        "failed_files": failed_files,
    }


def post_video_baijiahao(
    title,
    files,
    tags,
    account_file,
    category=None,
    enableTimer=False,
    videos_per_day=1,
    daily_times=None,
    start_days=0,
    description="",
    thumbnail_path="",
):
    """
    百家号视频发布函数 - 使用Playwright模拟浏览器操作

    参数:
        title: 视频标题
        files: 视频文件列表
        tags: 标签列表
        account_file: 账号cookie文件列表
        category: 视频分区（暂不支持）
        enableTimer: 是否启用定时发布
        videos_per_day: 每天发布视频数
        daily_times: 每天发布时间点列表
        start_days: 开始天数
        description: 视频简介
        thumbnail_path: 封面图片路径

    返回:
        dict: {"success": bool, "failed_files": list}
    """
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]

    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(
            len(files), videos_per_day, daily_times, start_days
        )
    else:
        publish_datetimes = [0 for _ in range(len(files))]

    failed_files = []
    success_count = 0

    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")

            try:
                app = BaiJiaHaoVideo(
                    title=title,
                    file_path=str(file),
                    tags=tags,
                    publish_date=publish_datetimes[index],
                    account_file=str(cookie),
                    description=description,
                )
                asyncio.run(app.main(), debug=False)
                print(f"✅ {file.name} 上传成功")
                success_count += 1
            except Exception as e:
                print(f"❌ 上传视频 {file.name} 时出错: {str(e)}")
                import traceback

                traceback.print_exc()
                failed_files.append(str(file.name))

    return {
        "success": len(failed_files) == 0,
        "success_count": success_count,
        "failed_count": len(failed_files),
        "failed_files": failed_files,
    }


# post_video("333",["demo.mp4"],"d","d")
# post_video_DouYin("333",["demo.mp4"],"d","d")
